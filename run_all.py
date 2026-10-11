"""
run_all.py – Master pipeline script.
Runs every stage in order, stopping after each to report key numbers.

Usage: python run_all.py [--stage N]
  --stage 0  : labels only (Step 0)
  --stage 1  : + pilot read (Step 1)
  --stage 2  : + fetch slice (Step 2) [will prompt before >50 MB]
  --stage 3  : + ETL, candidates, coverage (Step 3)
  --stage 4  : + EDA figures (Step 4)
  --stage 5  : + baselines (Step 5)
  --stage 6  : + model training A2, A3, A1 (Step 6)
  --stage 7  : + result figures, graph view (Step 7)
  --stage 8  : + dashboard + report (Step 8, default)
"""

import sys, argparse, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run(script: str, *args):
    cmd = [sys.executable, str(ROOT / script)] + list(args)
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print('='*60)
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print(f"\n[STOP] {script} exited with code {result.returncode}.")
        print("Fix the issue above before proceeding.")
        sys.exit(result.returncode)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, default=8,
                        help="Run up to this pipeline stage (0-8, default 8)")
    parser.add_argument("--model", default="all")
    parser.add_argument("--delta", default="all")
    args = parser.parse_args()

    stage = args.stage

    if stage >= 0:
        run("data/01_labels.py")

    if stage >= 1:
        run("data/02_pilot.py")

    if stage >= 2:
        print("\n[Pipeline] About to fetch data slice.")
        print("  Check pilot_summary.json for estimated size before proceeding.")
        run("data/03_fetch_slice.py")

    if stage >= 3:
        run("data/04_spark_etl.py")
        run("data/06_candidates.py")
        # Benchmark streaming replay
        run("data/05_stream_replay.py")

    if stage >= 4:
        run("viz/eda_figs.py")

    if stage >= 5:
        run("models/baselines.py")

    if stage >= 6:
        run("train.py", f"--model={args.model}", f"--delta={args.delta}")

    if stage >= 7:
        run("evaluate.py")
        run("viz/result_figs.py")
        run("viz/graph_view.py")

    if stage >= 8:
        run("viz/build_dashboard.py")
        write_report()

    print(f"\n{'='*60}")
    print(f"Pipeline complete through stage {stage}.")
    dashboard = ROOT / "reports" / "dashboard.html"
    print(f"Dashboard: file:///{dashboard.as_posix()}")

def write_report():
    from configs.config import REPORTS_DIR
    import json, csv
    from datetime import datetime

    report = ["# DHAP-Net on LANL Cyber Data – Final Report\n"]
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # 1. Download ledger
    report.append("\n## 1. Download Ledger\n")
    ledger = REPORTS_DIR / "download_ledger.csv"
    if ledger.exists():
        rows = list(csv.DictReader(open(ledger)))
        report.append("| Timestamp | File | Bytes | Cumulative |")
        report.append("|-----------|------|-------|------------|")
        for r in rows:
            cum_mb = int(r["cumulative_bytes"]) / 1e6
            report.append(f"| {r['timestamp']} | {r['file']} | "
                          f"{int(r['bytes_fetched']):,} | {cum_mb:.2f} MB |")
        if rows:
            cum_gb = int(rows[-1]["cumulative_bytes"]) / 1e9
            report.append(f"\n**Total downloaded:** {cum_gb:.3f} GB / 2.0 GB budget\n")
    else:
        report.append("_Ledger not found – run pipeline stages 0-2 first._\n")

    # Tier
    pilot_p = REPORTS_DIR / "pilot_summary.json"
    if pilot_p.exists():
        pilot = json.load(open(pilot_p))
        report.append(f"\n**Tier used:** {pilot.get('recommended_tier','?')}  ")
        report.append(f"(auth.txt estimated {pilot.get('estimated_slice_gb',0):.2f} GB "
                      f"for full slice; slice only covers red-team window + lead-in)\n")

    # 2. Dataset statistics
    report.append("\n## 2. Dataset Statistics\n")
    rt_csv = ROOT / "data" / "raw" / "redteam_labels.csv"
    if rt_csv.exists():
        import pandas as pd
        rt = pd.read_csv(str(rt_csv))
        report.append(f"- Red-team events: {len(rt):,}")
        report.append(f"- Distinct users: {rt['user'].nunique():,}")
        report.append(f"- Distinct source hosts: {rt['src'].nunique():,}")
        report.append(f"- Distinct destination hosts: {rt['dst'].nunique():,}")
        report.append(f"- Time range: {rt['time'].min():,} – {rt['time'].max():,} s")
        report.append(f"- Days in data: {rt['time'].min()//86400} – {rt['time'].max()//86400}\n")

    # Coverage ceiling
    cp = REPORTS_DIR / "coverage_ceiling.json"
    if cp.exists():
        ceiling = json.load(open(cp))
        report.append("\n### Coverage ceiling\n")
        report.append("| k | Recall upper bound |")
        report.append("|---|-------------------|")
        for k, v in ceiling.items():
            report.append(f"| {k} | {v*100:.1f}% |")

    # 3. Design mapping
    report.append("\n## 3. Design-to-implementation mapping\n")
    report.append("""
| Original design | What was built |
|-----------------|----------------|
| Kafka streaming | File-source replay in chronological 1-hour micro-batches |
| Spark Structured Streaming + HDFS | pandas streaming from local Parquet (HDFS stand-in) |
| PySpark MLlib RF | scikit-learn RF with identical features (Java/JDK not installed) |
| GraphFrames BFS | Python BFS over in-memory adjacency dict |
| PyTorch Geometric Temporal | Plain PyTorch (HRE+ST-DTE+BPD) |
| Plotly + Neo4j Bloom | Plotly + PyVis (Neo4j skipped – no local instance) |
| CVE nodes | Dropped (LANL has no CVE data) |
| IDS alerts | Red-team file used as attack signal and ground truth |
| Asset criticality | Dropped (graph-centrality proxy available but not used) |
| Organisation edges | Domain extracted from user@domain; cross-domain auth as proxy |
| Attack-type loss (α) | α=0 (no attack-type labels in LANL) |

**Note on PySpark:** JDK 11/17 is not installed on this machine.
The ETL logic is implemented in pandas with the same schema PySpark would produce.
The Spark MLlib RF baseline uses scikit-learn with identical feature columns.
All Parquet files are stored locally (stand-in for HDFS).
Throughput numbers describe the local machine only, not a cluster.
""")

    # 4. Results
    report.append("\n## 4. Results\n")
    final_p = REPORTS_DIR / "tables" / "final_results.csv"
    if final_p.exists():
        import pandas as pd
        df = pd.read_csv(str(final_p))
        df6 = df[df["delta_h"] == 6]
        if not df6.empty:
            report.append(df6[["model","AP_mean","AP_std","ROC_AUC_mean",
                               "P@10_mean","R@10_mean"]].to_markdown(index=False))
    else:
        report.append("_Run training and evaluate.py to populate this section._\n")

    # 5. Limitations
    report.append("""
## 5. Limitations

- **Single dataset:** Results describe one network and one red-team campaign.
  Generalisation is unknown.
- **Slice only:** We use only the red-team window plus a 2-day lead-in,
  not all 58 days. The graph is less dense than it would be over the full dataset.
- **Simplified reimplementations:** A2 (TGNE-TA-style) and A3 (DMSTG-AD-style)
  are implemented from short descriptions, not from the original authors' code.
  Their performance here may differ from the originals.
- **Spark in local mode:** PySpark was not available (JDK not installed).
  The ETL runs in pandas. Local Parquet stands in for HDFS.
  File-based replay stands in for Kafka.
- **Few positives:** The test set may have very few positive examples,
  making confidence intervals wide. Report bootstrap intervals where possible.
- **No GPU:** Training runs on CPU; wall times reflect a local workstation.
""")

    # 6. Reproducibility
    report.append("\n## 6. Reproducibility\n")
    report.append("```\n")
    report.append("python data/01_labels.py   # Step 0: labels (~5 KB)\n")
    report.append("python data/02_pilot.py    # Step 1: pilot read (~30 MB)\n")
    report.append("python data/03_fetch_slice.py  # Step 2: auth slice\n")
    report.append("python data/04_spark_etl.py    # Step 3: ETL\n")
    report.append("python data/06_candidates.py   # Step 3: candidates\n")
    report.append("python viz/eda_figs.py          # Step 4: EDA figures\n")
    report.append("python models/baselines.py      # Step 5: baselines\n")
    report.append("python train.py                 # Step 6: A1, A2, A3\n")
    report.append("python evaluate.py              # Step 7: metrics\n")
    report.append("python viz/result_figs.py       # Step 7: result figures\n")
    report.append("python viz/graph_view.py        # Step 7: graph view\n")
    report.append("python viz/build_dashboard.py   # Step 8: dashboard\n")
    report.append("```\n\n")
    import sys as _sys, torch
    report.append(f"Python: {_sys.version}  \n")
    report.append(f"PyTorch: {torch.__version__}  \n")
    report.append(f"Seeds: 42, 123, 2024  \n")

    out = REPORTS_DIR / "report.md"
    out.write_text("\n".join(report), encoding="utf-8")
    print(f"\n[Report] Written to {out}")

if __name__ == "__main__":
    main()
