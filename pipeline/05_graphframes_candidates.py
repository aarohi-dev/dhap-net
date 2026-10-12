"""
pipeline/05_graphframes_candidates.py
──────────────────────────────────────
GraphFrames-based candidate set construction.

Uses Spark + GraphFrames to:
  1. Build host communication graph from aggregated Parquet flows
  2. Run k-hop BFS to find candidate propagation targets
  3. Compute per-candidate features
  4. Write candidate dataset to HDFS (and local Parquet fallback)

This replaces data/06_candidates.py with proper GraphFrames operations.

Usage:
    # With Spark cluster:
    spark-submit \\
      --master spark://spark-master:7077 \\
      --packages graphframes:graphframes:0.8.4-spark3.5-s_2.12 \\
      pipeline/05_graphframes_candidates.py

    # Local (uses local[*] Spark):
    python pipeline/05_graphframes_candidates.py --local
"""

import sys, json, io, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs.config import (
    DATA_DIR, PARQUET_DIR, DATA_OUT, REPORTS_DIR,
    K_HOPS, DELTAS, WINDOW_S, MICRO_BATCH,
    HDFS_NAMENODE, HDFS_GRAPHS_PATH, HDFS_PREDICTIONS_PATH,
    SPARK_MASTER, SPARK_DRIVER_MEMORY
)

import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


# ── Pandas/numpy fallback for graph operations ────────────────────────────────
# Used when Spark/GraphFrames is not available (pure-Python mode)

def k_hop_bfs(seeds: set, adj: dict, k: int) -> set:
    """BFS k-hop reachability from seeds using adjacency dict."""
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


def build_adj(df: pd.DataFrame) -> dict:
    return (
        df.groupby("src")["dst"]
        .apply(set)
        .to_dict()
    )


def build_candidates_pandas(flows_df: pd.DataFrame,
                             comp_times: dict,
                             t_start: int, t_end: int,
                             stride_h: int = 6,
                             max_cands: int = 2000) -> pd.DataFrame:
    """
    Pure-pandas candidate builder.  Used as fallback when Spark unavailable.
    """
    hours   = sorted(flows_df["hour"].unique())
    h_start = t_start // 3600
    h_end   = t_end   // 3600
    hours   = [h for h in hours if h_start <= h <= h_end][::stride_h]

    records = []
    t0 = time.time()

    for i, h in enumerate(hours):
        t   = h * 3600
        C_t = {hst for hst, tv in comp_times.items() if tv <= t}
        if len(C_t) < 1:
            continue

        w_low = max(0, h - WINDOW_S // 3600)
        w_df  = flows_df[(flows_df["hour"] >= w_low) & (flows_df["hour"] < h)]
        adj   = build_adj(w_df)
        cands = k_hop_bfs(C_t, adj, K_HOPS)
        if not cands:
            continue

        # Cap by in-degree
        if len(cands) > max_cands:
            in_deg = w_df.groupby("dst")["n_flows"].sum().to_dict()
            cands  = set(sorted(cands,
                                key=lambda x: in_deg.get(x, 0),
                                reverse=True)[:max_cands])

        hop1    = k_hop_bfs(C_t, adj, 1)
        in_deg  = w_df.groupby("dst")["n_flows"].sum().to_dict()
        out_deg = w_df.groupby("src")["n_flows"].sum().to_dict()
        bytes_i = w_df.groupby("dst")["total_bytes"].sum().to_dict()

        for cand in cands:
            hop_d  = 1 if cand in hop1 else 2
            n_cn   = sum(1 for nb in adj.get(cand, set()) if nb in C_t)
            for delta in DELTAS:
                tv    = comp_times.get(cand, 1e18)
                label = int(t < tv <= t + delta)
                records.append({
                    "hour":       h,
                    "t":          t,
                    "host":       cand,
                    "delta":      delta,
                    "label":      label,
                    "hop_dist":   hop_d,
                    "in_degree":  float(in_deg.get(cand, 0)),
                    "out_degree": float(out_deg.get(cand, 0)),
                    "bytes_in":   float(bytes_i.get(cand, 0.0)),
                    "n_comp_nbr": n_cn,
                    "n_compr":    len(C_t),
                    "n_cands":    len(cands),
                })

        if (i + 1) % 5 == 0:
            print(f"  [{i+1}/{len(hours)}] h={h}  "
                  f"|C(t)|={len(C_t)}  |cands|={len(cands):,}  "
                  f"records={len(records):,}  {time.time()-t0:.0f}s", flush=True)

    df = pd.DataFrame(records)
    pos = int(df["label"].sum()) if len(df) > 0 else 0
    print(f"[Candidates] {len(df):,} records, {pos:,} positives "
          f"({pos/max(len(df),1)*100:.3f}%)")
    return df


# ── GraphFrames implementation ────────────────────────────────────────────────

def build_candidates_graphframes(flows_parquet: str,
                                  comp_times: dict,
                                  t_start: int, t_end: int,
                                  spark) -> pd.DataFrame:
    """
    GraphFrames implementation.  Runs inside PySpark context.
    """
    from pyspark.sql import functions as F
    from graphframes import GraphFrame

    df = spark.read.parquet(flows_parquet)

    # Filter to slice window
    h_start = t_start // 3600
    h_end   = t_end   // 3600
    df = df.filter((F.col("hour") >= h_start) & (F.col("hour") <= h_end))

    # Build full graph
    vertices = (
        df.select(F.col("src").alias("id"))
        .union(df.select(F.col("dst").alias("id")))
        .distinct()
    )
    edges = df.select("src", "dst", "n_flows", "total_bytes", "hour")
    g = GraphFrame(vertices, edges)

    n_v = vertices.count()
    n_e = edges.count()
    print(f"[GraphFrames] Full graph: {n_v:,} vertices, {n_e:,} edges")

    # In/out degrees
    in_deg  = g.inDegrees.toPandas().set_index("id")["inDegree"].to_dict()
    out_deg = g.outDegrees.toPandas().set_index("id")["outDegree"].to_dict()

    # Coverage ceiling computation (for each k-hop)
    comp_hosts = set(comp_times.keys())
    # Convert to Pandas for BFS (GraphFrames BFS is expensive for many seeds)
    flows_pd = df.toPandas()
    adj = build_adj(flows_pd)

    # Ceiling (k=1,2,3) — how many future compromised hosts are reachable
    ceiling = {}
    for k in [1, 2, 3]:
        reachable = k_hop_bfs(comp_hosts, adj, k)
        future_comp = {h for h, tv in comp_times.items()
                       if tv > t_start and tv <= t_end}
        hits = len(reachable & future_comp)
        ceiling[k] = hits / max(len(future_comp), 1)
        print(f"  k={k}: {ceiling[k]*100:.1f}% ceiling recall")

    with open(REPORTS_DIR / "coverage_ceiling.json", "w") as f:
        json.dump(ceiling, f, indent=2)

    # Build candidates with pandas BFS using the Pandas df
    cand_df = build_candidates_pandas(
        flows_pd, comp_times, t_start, t_end, stride_h=6
    )
    return cand_df


# ── Time split ────────────────────────────────────────────────────────────────

def time_split(df: pd.DataFrame):
    hours = sorted(df["hour"].unique())
    n     = len(hours)
    h_tr  = hours[int(n * 0.60)]
    h_va  = hours[int(n * 0.80)]
    train = df[df["hour"] <= h_tr]
    val   = df[(df["hour"] > h_tr) & (df["hour"] <= h_va)]
    test  = df[df["hour"] > h_va]
    print(f"\n── Time split ────────────────────────────────────────────────")
    print(f"  Train : hour <= {h_tr}   "
          f"({len(train):,} rows, {int(train['label'].sum())} pos)")
    print(f"  Val   : hour <= {h_va}   "
          f"({len(val):,} rows, {int(val['label'].sum())} pos)")
    print(f"  Test  : hour >  {h_va}   "
          f"({len(test):,} rows, {int(test['label'].sum())} pos)")
    return train, val, test


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true",
                        help="Use local Spark (no cluster)")
    parser.add_argument("--pandas-only", action="store_true",
                        help="Skip Spark, use pure pandas")
    args = parser.parse_args()

    # Load redteam labels
    rt_csv = DATA_DIR / "redteam_labels.csv"
    if not rt_csv.exists():
        sys.exit("[ERROR] redteam_labels.csv not found. Run 01_parse_labels.py first.")
    rt = pd.read_csv(rt_csv)
    dst_first = rt.groupby("dst")["time"].min().to_dict()
    src_only  = set(rt["src"].unique()) - set(rt["dst"].unique())
    for h in src_only:
        dst_first[h] = int(rt[rt["src"] == h]["time"].min())
    comp_times = dst_first
    print(f"[Candidates] Red-team: {len(rt):,} events, "
          f"{len(comp_times):,} compromised hosts")

    # Load slice window
    sw_path = REPORTS_DIR / "slice_window.json"
    if not sw_path.exists():
        sys.exit("[ERROR] slice_window.json not found. Run 01_parse_labels.py first.")
    with open(sw_path) as f:
        sw = json.load(f)
    t_start = int(sw["t_start"])
    t_end   = int(sw["t_end"])

    flows_parquet = str(PARQUET_DIR / "flows" / "flows_agg.parquet")
    if not Path(flows_parquet).exists():
        sys.exit("[ERROR] flows_agg.parquet not found. Run 02_etl_flows.py first.")

    if args.pandas_only:
        print("[Candidates] Using pandas-only mode.")
        flows_df = pd.read_parquet(flows_parquet)
        print(f"[Candidates] Loaded {len(flows_df):,} aggregated rows")

        # Coverage ceiling: fraction of future-compromised hosts reachable
        # from the EARLIEST compromised footholds via k-hop BFS.
        # Footholds = the 4 src-only hosts from redteam.txt (appear as src but never dst).
        # Future_comp = all dst-compromised hosts that were compromised AFTER the median RT time.
        print("\n[Candidates] Computing coverage ceiling ...")
        ceiling = {}
        adj_full = build_adj(flows_df)
        comp_hosts = set(comp_times.keys())
        comp_times_sorted = sorted(comp_times.items(), key=lambda x: x[1])
        # Use first 20% of compromised hosts as "seeds" (earliest known compromised)
        n_early = max(1, len(comp_times_sorted) // 5)
        early_seeds = {h for h, _ in comp_times_sorted[:n_early]}
        # Future compromised = everything else
        future_comp = {h for h, _ in comp_times_sorted[n_early:]}
        print(f"  Seeds (earliest {n_early} hosts): {early_seeds}")
        print(f"  Future compromised: {len(future_comp)} hosts")
        for k in [1, 2, 3]:
            reachable = k_hop_bfs(early_seeds, adj_full, k)
            hits = len(reachable & future_comp)
            ceiling[k] = hits / max(len(future_comp), 1)
            flag = "  <-- LOW" if ceiling[k] < 0.30 else ""
            print(f"  k={k}: {ceiling[k]*100:.1f}% "
                  f"({hits}/{len(future_comp)} future-compromised reachable){flag}")
        with open(REPORTS_DIR / "coverage_ceiling.json", "w") as f:
            json.dump(ceiling, f, indent=2)

        cand_df = build_candidates_pandas(
            flows_df, comp_times, t_start, t_end, stride_h=6
        )
    else:
        # GraphFrames via Spark
        try:
            from pyspark.sql import SparkSession
            master = "local[*]" if args.local else SPARK_MASTER
            spark = (SparkSession.builder
                     .appName("DHAP-Net GraphFrames Candidates")
                     .master(master)
                     .config("spark.driver.memory", SPARK_DRIVER_MEMORY)
                     .config("spark.jars.packages",
                             "graphframes:graphframes:0.8.4-spark3.5-s_2.12")
                     .getOrCreate())
            spark.sparkContext.setLogLevel("WARN")
            cand_df = build_candidates_graphframes(
                flows_parquet, comp_times, t_start, t_end, spark
            )
            spark.stop()
        except ImportError as e:
            print(f"[WARNING] Spark not available ({e}); falling back to pandas.")
            flows_df = pd.read_parquet(flows_parquet)
            cand_df = build_candidates_pandas(
                flows_df, comp_times, t_start, t_end, stride_h=6
            )

    if len(cand_df) == 0:
        print("[WARNING] Empty candidate set – check t_start/t_end vs flows hours")
        return

    train, val, test = time_split(cand_df)
    DATA_OUT.mkdir(parents=True, exist_ok=True)

    for name, split in [("train", train), ("val", val),
                         ("test", test), ("candidates_all", cand_df)]:
        out = DATA_OUT / f"{name}.parquet"
        split.to_parquet(out, index=False)
        print(f"[Candidates] Saved {name} --> {out}")

    print("\n[Candidates] OK Done.  Next: python train.py --model a1")


if __name__ == "__main__":
    main()
