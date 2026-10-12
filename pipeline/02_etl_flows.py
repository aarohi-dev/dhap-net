"""
pipeline/02_etl_flows.py
────────────────────────
ETL: Parse reports/data/flows.txt --> Parquet aggregations.

This is the canonical ETL for the ONLY permitted dataset.

LANL flows.txt schema (no header, comma-separated, 9 fields):
    time       int   seconds since capture start
    duration   int   flow duration (s)
    src        str   anonymised source host  (e.g. C1065)
    src_port   str   source port / service   (e.g. 389, N10451)
    dst        str   anonymised destination host
    dst_port   str   destination port / service
    protocol   int   IP protocol (6=TCP, 17=UDP, 1=ICMP)
    packets    int   packet count
    bytes      int   byte count

Usage:
    python pipeline/02_etl_flows.py
"""

import sys, time, json, io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs.config import FLOWS_TXT, PARQUET_DIR, REPORTS_DIR, FLOWS_COLS

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

CHUNK_ROWS = 1_000_000   # lines per processing chunk

# Every chunk is cast to this exact set of dtypes before writing.
FINAL_DTYPES = {
    "day":           "int32",
    "hour":          "int32",
    "protocol":      "int32",
    "n_flows":       "int64",
    "total_bytes":   "float64",
    "total_packets": "float64",
}


def parse_chunk(lines: list) -> tuple:
    """Parse raw CSV lines into a typed DataFrame. Returns (df, n_bad)."""
    records = []
    bad = 0
    for ln in lines:
        parts = ln.strip().split(",")
        if len(parts) < 9:
            bad += 1
            continue
        records.append(parts[:9])

    if not records:
        return pd.DataFrame(), bad

    df = pd.DataFrame(records, columns=FLOWS_COLS)
    for col in ["time", "duration", "protocol", "packets", "bytes_val"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.dropna(subset=["time", "src", "dst"], inplace=True)
    if df.empty:
        return df, bad

    df = df.astype({"time": "int64", "protocol": "Int32",
                    "packets": "Int64", "bytes_val": "Int64"})
    df["hour"] = (df["time"] // 3600).astype("int32")
    df["day"]  = (df["time"] // 86400).astype("int32")
    return df, bad


def aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate raw flows to hourly edge-level counts."""
    agg = (
        df.groupby(["day", "hour", "src", "dst", "protocol"])
          .agg(
              n_flows       = ("time",      "count"),
              total_bytes   = ("bytes_val", "sum"),
              total_packets = ("packets",   "sum"),
          )
          .reset_index()
    )
    # Enforce consistent dtypes so every chunk has an identical Parquet schema
    for col, dtype in FINAL_DTYPES.items():
        if col in agg.columns:
            agg[col] = agg[col].astype(dtype)
    return agg


def etl_flows():
    if not FLOWS_TXT.exists():
        sys.exit(f"[ETL] ERROR: flows.txt not found at {FLOWS_TXT}")

    size_gb = FLOWS_TXT.stat().st_size / 1e9
    print(f"\n[ETL] flows.txt  size={size_gb:.2f} GB  path={FLOWS_TXT}")

    out_dir = PARQUET_DIR / "flows"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_agg = out_dir / "flows_agg.parquet"

    # Remove any stale partial output
    if out_agg.exists():
        out_agg.unlink()

    writer    = [None]   # list so inner code can mutate it
    total_raw = 0
    total_agg = 0
    total_bad = 0

    def write_chunk(lines: list) -> int:
        """Parse + aggregate + write a chunk. Returns number of bad lines."""
        df, bad = parse_chunk(lines)
        if df is None or df.empty:
            return bad
        agg = aggregate(df)
        tbl = pa.Table.from_pandas(agg, preserve_index=False)
        if writer[0] is None:
            writer[0] = pq.ParquetWriter(str(out_agg), tbl.schema,
                                          compression="snappy")
        writer[0].write_table(tbl)
        return bad, len(agg)

    print("[ETL] Reading and aggregating (single pass) ...")
    t0  = time.time()
    buf = []

    with open(FLOWS_TXT, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            buf.append(line)
            total_raw += 1
            if len(buf) >= CHUNK_ROWS:
                result = write_chunk(buf)
                if isinstance(result, tuple):
                    bad_c, agg_c = result
                else:
                    bad_c, agg_c = result, 0
                total_bad += bad_c
                total_agg += agg_c
                buf = []
                elapsed = time.time() - t0
                print(f"\r  raw={total_raw/1e6:.1f}M  agg={total_agg:,}  "
                      f"bad={total_bad:,}  {elapsed:.0f}s ...",
                      end="", flush=True)

    if buf:
        result = write_chunk(buf)
        if isinstance(result, tuple):
            bad_c, agg_c = result
        else:
            bad_c, agg_c = result, 0
        total_bad += bad_c
        total_agg += agg_c

    if writer[0] is not None:
        writer[0].close()

    elapsed = time.time() - t0
    print(f"\n[ETL] Done in {elapsed:.0f}s")
    print(f"  Raw lines processed  : {total_raw:,}")
    print(f"  Malformed / rejected : {total_bad:,}")
    print(f"  Aggregated rows      : {total_agg:,}")
    print(f"  Output               : {out_agg}")

    print("\n[ETL] Computing summary statistics ...")
    t1  = time.time()
    df_full = pd.read_parquet(str(out_agg))
    print(f"  Hour range   : {df_full['hour'].min()} -> {df_full['hour'].max()}")
    print(f"  Day range    : {df_full['day'].min()} -> {df_full['day'].max()}")
    print(f"  Unique src   : {df_full['src'].nunique():,}")
    print(f"  Unique dst   : {df_full['dst'].nunique():,}")
    proto_counts = (df_full.groupby("protocol")["n_flows"].sum()
                    .sort_values(ascending=False).to_dict())
    print(f"  Protocols    : {proto_counts}")
    print(f"  Stats in     : {time.time()-t1:.1f}s")

    meta = {
        "source":      str(FLOWS_TXT),
        "size_bytes":  FLOWS_TXT.stat().st_size,
        "raw_lines":   total_raw,
        "malformed":   total_bad,
        "agg_rows":    total_agg,
        "hour_min":    int(df_full["hour"].min()),
        "hour_max":    int(df_full["hour"].max()),
        "day_min":     int(df_full["day"].min()),
        "day_max":     int(df_full["day"].max()),
        "unique_src":  int(df_full["src"].nunique()),
        "unique_dst":  int(df_full["dst"].nunique()),
        "protocols":   {str(k): int(v) for k, v in proto_counts.items()},
        "etl_seconds": round(elapsed, 1),
        "schema":      "time,duration,src,src_port,dst,dst_port,protocol,packets,bytes",
        "dataset":     "LANL Unified Host and Network Dataset (netflow)",
        "labels":      "redteam.txt (confirmed red-team authentication events)",
    }
    meta_path = REPORTS_DIR / "fetch_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"\n[ETL] Meta -> {meta_path}")
    print("\n[ETL] Done.  Next: python pipeline/05_graphframes_candidates.py --pandas-only")
    return meta


if __name__ == "__main__":
    etl_flows()
