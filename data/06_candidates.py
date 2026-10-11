"""
Step 5 – Build candidate sets and labels for each micro-batch.
Vectorised implementation — avoids row-by-row iteration on the full flows parquet.

Strategy:
  - Pre-build adjacency dict once per WINDOW_S sliding window (rebuilt hourly).
  - Use numpy/set operations for k-hop BFS, not iterrows().
  - Sample every STRIDE hours to keep runtime tractable.
  - Cap candidates per micro-batch at MAX_CANDS to avoid OOM.

Run: python data/06_candidates.py
"""

import sys, json, io, collections, time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs.config import (
    DATA_DIR, PARQUET_DIR, REPORTS_DIR, DATA_OUT,
    K_HOPS, DELTAS, WINDOW_S, MICRO_BATCH
)

import pandas as pd
import numpy as np
import pyarrow.parquet as pq
import pyarrow as pa

STRIDE    = 6        # evaluate every 6 hours (reduces candidate steps 128 -> 21)
MAX_CANDS = 2000     # cap candidates per micro-batch
MIN_C_T   = 1        # skip hours with no compromised hosts yet

# ── load labels ───────────────────────────────────────────────────────────────
def load_labels():
    rt_path = DATA_DIR / "redteam_labels.csv"
    if not rt_path.exists():
        sys.exit("[ERROR] redteam_labels.csv not found. Run 01_labels.py first.")
    rt = pd.read_csv(rt_path)
    dst_first = rt.groupby("dst")["time"].min().to_dict()
    src_only  = set(rt["src"].unique()) - set(rt["dst"].unique())
    for h in src_only:
        dst_first[h] = int(rt[rt["src"] == h]["time"].min())
    print(f"[Candidates] Red-team: {len(rt):,} events, "
          f"{len(dst_first):,} compromised hosts (incl. {len(src_only)} footholds)")
    return rt, dst_first

# ── vectorised adjacency builder ──────────────────────────────────────────────
def build_adj_vectorised(flows_df: pd.DataFrame, h_low: int, h_high: int) -> dict:
    """Build adjacency from src->set(dst) using vectorised groupby."""
    mask = (flows_df["hour"] >= h_low) & (flows_df["hour"] < h_high)
    sub  = flows_df[mask][["src","dst"]].dropna()
    if sub.empty:
        return {}
    # Group all destinations per source in one pass
    adj = (sub.groupby("src")["dst"]
           .apply(set)
           .to_dict())
    return adj

# ── BFS k-hop ─────────────────────────────────────────────────────────────────
def k_hop(seeds: set, adj: dict, k: int) -> set:
    visited  = set(seeds)
    frontier = set(seeds)
    for _ in range(k):
        nxt = set()
        for n in frontier:
            for m in adj.get(n, set()):
                if m not in visited:
                    nxt.add(m)
                    visited.add(m)
        frontier = nxt
    return visited - seeds

# ── coverage ceiling (sampled) ────────────────────────────────────────────────
def coverage_ceiling(comp_times, flows_df, t_start, t_end, delta=6*3600):
    results  = {1: [], 2: [], 3: []}
    hours    = sorted(flows_df["hour"].unique())
    stride_c = max(1, len(hours) // 20)    # at most 20 probes

    t0 = time.time()
    for i, h in enumerate(hours[::stride_c]):
        t = h * 3600
        C_t  = {hst for hst, tv in comp_times.items() if tv <= t}
        nvx  = {hst for hst, tv in comp_times.items() if t < tv <= t+delta}
        if not C_t or not nvx:
            continue
        w_low = max(0, h - WINDOW_S//3600)
        adj   = build_adj_vectorised(flows_df, w_low, h)
        for k in [1, 2, 3]:
            cands = k_hop(C_t, adj, k)
            hits  = len(nvx & cands)
            results[k].append(hits / len(nvx))

    print(f"[Candidates] Coverage ceiling computed in {time.time()-t0:.1f}s")
    return {k: float(np.mean(v)) if v else 0.0 for k, v in results.items()}

# ── build candidate dataset ────────────────────────────────────────────────────
def build_candidates(flows_df, comp_times, t_start, t_end):
    hours   = sorted(flows_df["hour"].unique())
    h_start = t_start // 3600
    h_end   = t_end   // 3600
    hours   = [h for h in hours if h_start <= h <= h_end][::STRIDE]

    records = []
    t0      = time.time()
    for i, h in enumerate(hours):
        t   = h * 3600
        C_t = {hst for hst, tv in comp_times.items() if tv <= t}
        if len(C_t) < MIN_C_T:
            continue

        w_low = max(0, h - WINDOW_S//3600)
        adj   = build_adj_vectorised(flows_df, w_low, h)
        cands = k_hop(C_t, adj, K_HOPS)
        if not cands:
            continue

        # Cap to MAX_CANDS by risk-proxy (in-degree)
        if len(cands) > MAX_CANDS:
            mask   = flows_df["hour"] >= w_low
            in_deg = flows_df[mask].groupby("dst")["n_flows"].sum().to_dict()
            cands  = set(sorted(cands,
                                key=lambda x: in_deg.get(x, 0),
                                reverse=True)[:MAX_CANDS])

        hop1 = k_hop(C_t, adj, 1)
        # Aggregate features
        w_df    = flows_df[(flows_df["hour"] >= w_low) & (flows_df["hour"] < h)]
        in_deg  = w_df.groupby("dst")["n_flows"].sum().to_dict()
        out_deg = w_df.groupby("src")["n_flows"].sum().to_dict()
        bytes_in= w_df.groupby("dst")["total_bytes"].sum().to_dict()

        for cand in cands:
            hop_d = 1 if cand in hop1 else 2
            n_cn  = sum(1 for nbr in adj.get(cand, set()) if nbr in C_t)
            for delta in DELTAS:
                tv    = comp_times.get(cand, 1e18)
                label = int(t < tv <= t + delta)
                records.append({
                    "hour": h, "t": t, "host": cand, "delta": delta,
                    "label": label,
                    "hop_dist":   hop_d,
                    "in_degree":  float(in_deg.get(cand, 0)),
                    "out_degree": float(out_deg.get(cand, 0)),
                    "bytes_in":   float(bytes_in.get(cand, 0.0)),
                    "n_comp_nbr": n_cn,
                    "n_compr":    len(C_t),
                    "n_cands":    len(cands),
                })

        if (i+1) % 5 == 0:
            elapsed = time.time() - t0
            print(f"  [{i+1}/{len(hours)}] h={h:3d}  "
                  f"|C(t)|={len(C_t):3d}  |cands|={len(cands):,}  "
                  f"records={len(records):,}  {elapsed:.0f}s", flush=True)

    df  = pd.DataFrame(records)
    pos = df["label"].sum() if len(df) > 0 else 0
    print(f"[Candidates] {len(df):,} records, {pos:,} positives "
          f"({pos/max(len(df),1)*100:.3f}%)")
    return df

# ── time split ─────────────────────────────────────────────────────────────────
def time_split(df):
    hours = sorted(df["hour"].unique())
    n     = len(hours)
    h_tr  = hours[int(n * 0.60)]
    h_va  = hours[int(n * 0.80)]
    train = df[df["hour"] <= h_tr]
    val   = df[(df["hour"] > h_tr) & (df["hour"] <= h_va)]
    test  = df[df["hour"] > h_va]
    print(f"\n--- Time split ---")
    print(f"  Train: hour <= {h_tr}  Val: hour <= {h_va}  Test: hour > {h_va}")
    for name, sp in [("Train", train), ("Val", val), ("Test", test)]:
        for d in DELTAS:
            sub = sp[sp["delta"] == d]
            if len(sub) == 0:
                continue
            pos = int(sub["label"].sum())
            print(f"  {name} d={d//3600}h: {len(sub):,} rows, "
                  f"{pos} pos ({pos/max(len(sub),1)*100:.3f}%)")
    return train, val, test

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    flows_path = PARQUET_DIR / "flows" / "flows_agg.parquet"
    if not flows_path.exists():
        sys.exit("[ERROR] flows_agg.parquet not found. Run 04_spark_etl.py first.")

    print(f"[Candidates] Loading flows parquet ...")
    t0 = time.time()
    flows_df = pd.read_parquet(str(flows_path))
    print(f"  {len(flows_df):,} rows loaded in {time.time()-t0:.1f}s  "
          f"hours {flows_df['hour'].min()}–{flows_df['hour'].max()}")

    rt_df, comp_times = load_labels()

    with open(REPORTS_DIR / "slice_window.json") as f:
        sw = json.load(f)
    t_start = int(sw["t_start"])
    t_end   = int(sw["t_end"])

    # Only keep red-team events that fall within slice window
    real_comp = {h: tv for h, tv in comp_times.items() if tv <= t_end}
    print(f"[Candidates] Compromised hosts in slice window: {len(real_comp)} "
          f"(of {len(comp_times)} total)")

    # Coverage ceiling
    print(f"\n[Candidates] Computing coverage ceiling (d=6h, sampled) ...")
    ceiling = coverage_ceiling(real_comp, flows_df, t_start, t_end, 6*3600)
    print("\n--- Coverage ceiling ---")
    for k, v in ceiling.items():
        flag = "  <-- LOW recall cap" if v < 0.30 else ""
        print(f"  k={k}: {v*100:.1f}%{flag}")
    with open(REPORTS_DIR / "coverage_ceiling.json", "w") as f:
        json.dump(ceiling, f, indent=2)

    # Build candidates
    print(f"\n[Candidates] Building candidate dataset "
          f"(stride={STRIDE}h, max_cands={MAX_CANDS}) ...")
    cand_df = build_candidates(flows_df, real_comp, t_start, t_end)

    if len(cand_df) == 0:
        print("[WARNING] Empty candidate set!")
        return

    train, val, test = time_split(cand_df)
    DATA_OUT.mkdir(parents=True, exist_ok=True)
    for name, split in [("train", train), ("val", val),
                         ("test", test), ("candidates_all", cand_df)]:
        split.to_parquet(DATA_OUT / f"{name}.parquet", index=False)

    print(f"\n[Candidates] Saved to {DATA_OUT}")
    print("[Candidates] Done.")

if __name__ == "__main__":
    main()
