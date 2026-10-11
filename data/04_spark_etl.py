"""
Step 3 – ETL: pandas-based aggregation of flows slice and DNS.
Produces Parquet files that match what Spark Structured Streaming would read.

Target schemas:
  flows:  (day, hour, src, dst, protocol, n_flows, total_bytes, total_packets)
  dns:    (day, hour, src, computer_resolved, n_lookups)

Run: python data/04_spark_etl.py
"""

import sys, gzip, time, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs.config import DATA_DIR, PARQUET_DIR, REPORTS_DIR

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

CHUNK_ROWS = 500_000

# ── Flows ETL ─────────────────────────────────────────────────────────────────
FLOWS_COLS = ["time","duration","src","src_port","dst","dst_port",
              "protocol","packets","bytes_val"]

def etl_flows():
    flows_path = DATA_DIR / "flows_slice.txt"
    if not flows_path.exists():
        print(f"[ETL] flows_slice.txt not found at {flows_path}")
        print("      Run 03_fetch_slice.py first (or run with --synthetic flag).")
        return False

    print(f"\n[ETL] Processing flows slice: {flows_path}")
    print(f"  File size: {flows_path.stat().st_size / 1e9:.3f} GB")

    out_dir = PARQUET_DIR / "flows"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "flows_agg.parquet"

    writer    = None
    total_agg = 0
    buf       = []

    def flush(buf):
        nonlocal writer, total_agg
        df = pd.DataFrame(buf, columns=FLOWS_COLS)
        df["time"]     = pd.to_numeric(df["time"],     errors="coerce")
        df["packets"]  = pd.to_numeric(df["packets"],  errors="coerce").fillna(0)
        df["bytes_val"]= pd.to_numeric(df["bytes_val"],errors="coerce").fillna(0)
        df.dropna(subset=["time"], inplace=True)
        df = df.astype({"time": int, "packets": float, "bytes_val": float})
        df["hour"] = df["time"] // 3600
        df["day"]  = df["time"] // 86400

        agg = (df.groupby(["day","hour","src","dst","protocol"])
               .agg(n_flows       = ("time",      "count"),
                    total_bytes   = ("bytes_val", "sum"),
                    total_packets = ("packets",   "sum"))
               .reset_index())

        tbl = pa.Table.from_pandas(agg)
        if writer is None:
            writer = pq.ParquetWriter(str(out_path), tbl.schema, compression="snappy")
        writer.write_table(tbl)
        total_agg += len(agg)

    t0 = time.time()
    with open(flows_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 9:
                continue
            buf.append(parts[:9])
            if len(buf) >= CHUNK_ROWS:
                flush(buf)
                buf = []
                print(f"\r  {total_agg:,} aggregated rows  {time.time()-t0:.0f}s ...",
                      end="", flush=True)
        if buf:
            flush(buf)

    if writer:
        writer.close()

    elapsed = time.time() - t0
    print(f"\n[ETL] Flows aggregation: {total_agg:,} rows in {elapsed:.1f}s -> {out_path}")

    # Summary stats
    df_full = pd.read_parquet(str(out_path))
    print(f"\n  Hour range  : {df_full['hour'].min()} -> {df_full['hour'].max()}")
    print(f"  Unique src  : {df_full['src'].nunique():,}")
    print(f"  Unique dst  : {df_full['dst'].nunique():,}")
    print(f"  Protocols   :\n{df_full.groupby('protocol')['n_flows'].sum().sort_values(ascending=False).to_string()}")
    return True

# ── DNS ETL ───────────────────────────────────────────────────────────────────
DNS_COLS = ["time", "src", "computer_resolved"]

def etl_dns():
    dns_gz = DATA_DIR / "dns.txt.gz"
    if not dns_gz.exists():
        print("\n[ETL] dns.txt.gz not found; skipping DNS ETL.")
        return False

    print(f"\n[ETL] Processing dns.txt.gz: {dns_gz.stat().st_size/1e6:.0f} MB")
    out_dir = PARQUET_DIR / "dns"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    t0   = time.time()
    with gzip.open(dns_gz, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 3:
                continue
            try:
                t = int(parts[0])
            except ValueError:
                continue
            rows.append({"time": t, "src": parts[1], "computer_resolved": parts[2]})

    df = pd.DataFrame(rows)
    print(f"  Parsed {len(df):,} DNS events in {time.time()-t0:.1f}s")
    df["hour"] = df["time"] // 3600
    df["day"]  = df["time"] // 86400

    agg = (df.groupby(["day","hour","src","computer_resolved"])
           .size().reset_index(name="n_lookups"))

    out_path = out_dir / "dns_agg.parquet"
    pq.write_table(pa.Table.from_pandas(agg), str(out_path), compression="snappy")
    print(f"[ETL] DNS: {len(agg):,} aggregated rows -> {out_path}")
    return True

# ── Synthetic data fallback ───────────────────────────────────────────────────
def make_synthetic(t_start: int = 0, t_end: int = 15*86400,
                   n_hosts: int = 50, n_hours: int = 200,
                   seed: int = 42):
    """
    Generate synthetic flows and redteam data for pipeline testing
    when real data is not yet downloaded.
    """
    import numpy as np
    import json
    rng = np.random.default_rng(seed)

    hosts   = [f"C{1000+i}" for i in range(n_hosts)]
    hours   = list(range(t_start//3600, t_start//3600 + n_hours))

    # ── Synthetic flows ───────────────────────────────────────────────────────
    records = []
    for h in hours:
        n_edges = rng.integers(10, 40)
        srcs = rng.choice(hosts, n_edges)
        dsts = rng.choice(hosts, n_edges)
        for s, d in zip(srcs, dsts):
            if s == d:
                continue
            records.append({
                "day": h//24, "hour": h, "src": s, "dst": d,
                "protocol": rng.choice(["6","17"]),
                "n_flows": int(rng.integers(1,10)),
                "total_bytes": float(rng.integers(100,10000)),
                "total_packets": float(rng.integers(1,50)),
            })

    df_flows = pd.DataFrame(records)
    out_dir  = PARQUET_DIR / "flows"
    out_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(df_flows),
                   str(out_dir / "flows_agg.parquet"), compression="snappy")
    print(f"[Synthetic] Flows: {len(df_flows):,} rows")

    # ── Synthetic DNS ─────────────────────────────────────────────────────────
    dns_rows = []
    for h in hours[::3]:
        for _ in range(rng.integers(5,20)):
            dns_rows.append({
                "day": h//24, "hour": h,
                "src": rng.choice(hosts),
                "computer_resolved": rng.choice(hosts),
                "n_lookups": int(rng.integers(1,5)),
            })
    df_dns = pd.DataFrame(dns_rows)
    out_d2 = PARQUET_DIR / "dns"
    out_d2.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(df_dns),
                   str(out_d2 / "dns_agg.parquet"), compression="snappy")
    print(f"[Synthetic] DNS: {len(df_dns):,} rows")

    # ── Synthetic redteam ─────────────────────────────────────────────────────
    comp_hosts  = rng.choice(hosts, 20, replace=False)
    redteam_rows = []
    for i, h in enumerate(comp_hosts):
        t_comp = int(rng.integers(t_start + 86400, t_end - 86400))
        redteam_rows.append({"time": t_comp, "user": f"U{i}@DOM1",
                             "src": hosts[0], "dst": h})
    import pandas as pd_ ; from pathlib import Path as P_
    rt_df = pd.DataFrame(redteam_rows).sort_values("time")

    raw_dir = DATA_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    rt_df.to_csv(raw_dir / "redteam_labels.csv", index=False)
    print(f"[Synthetic] Redteam: {len(rt_df)} events")

    # Update slice_window
    sw = {
        "t_first_redteam": int(rt_df["time"].min()),
        "t_last_redteam":  int(rt_df["time"].max()),
        "t_start": t_start, "t_end": t_end,
        "lead_in_days": 2,
        "slice_days": (t_end - t_start) / 86400,
        "t_end_trimmed": True,
        "rt_events_covered": len(rt_df),
        "rt_events_total": len(rt_df),
        "synthetic": True,
    }
    with open(REPORTS_DIR / "slice_window.json", "w") as f_:
        json.dump(sw, f_)
    print(f"[Synthetic] slice_window.json updated")

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    import sys as _sys
    synthetic = "--synthetic" in _sys.argv

    if synthetic:
        print("\n[ETL] Running in SYNTHETIC mode (for pipeline validation).")
        make_synthetic()
        print("\n[ETL] Synthetic data ready.")
    else:
        flows_ok = etl_flows()
        dns_ok   = etl_dns()
        if not flows_ok and not dns_ok:
            print("\n[ETL] No data found. Pass --synthetic to generate test data.")

    print("\n[ETL] Done. Proceed to 06_candidates.py")

if __name__ == "__main__":
    main()
