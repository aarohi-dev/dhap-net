"""
run_pipeline.py
────────────────
Master pipeline orchestrator for DHAP-Net.

Executes the full pipeline in order:
  1. Parse red-team labels
  2. ETL: flows.txt → Parquet
  3. Start Kafka producer (background, optional)
  4. Run Spark Structured Streaming (optional)
  5. Build GraphFrames candidate sets
  6. Train DHAP-Net (A1, A2, A3)
  7. Run Spark MLlib baseline
  8. Export to Neo4j
  9. Build Plotly dashboard
  10. Run tests

Usage:
    # Full pipeline (requires all services running):
    python run_pipeline.py

    # Skip service-dependent steps (no Kafka/Spark/Neo4j needed):
    python run_pipeline.py --local

    # Just build candidates and train:
    python run_pipeline.py --local --skip-kafka --skip-neo4j

    # Start all Docker services first:
    docker compose up -d
    python run_pipeline.py
"""

import sys, subprocess, argparse, time, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from configs.config import FLOWS_TXT, DATA_DIR, DATA_OUT, PARQUET_DIR


def run(cmd: list, step: str):
    print(f"\n{'='*60}")
    print(f"[Pipeline] Step: {step}")
    print(f"  cmd: {' '.join(cmd)}")
    print(f"{'='*60}")
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=False)
    elapsed = time.time() - t0
    status = "✓ OK" if result.returncode == 0 else f"✗ FAILED (code {result.returncode})"
    print(f"[Pipeline] {step}: {status}  ({elapsed:.1f}s)")
    return result.returncode == 0


def check_prerequisites():
    print("[Pipeline] Checking prerequisites ...")
    ok = True
    if not FLOWS_TXT.exists():
        print(f"  ERROR: flows.txt not found at {FLOWS_TXT}")
        ok = False
    else:
        print(f"  ✓ flows.txt: {FLOWS_TXT.stat().st_size/1e9:.2f} GB")

    redteam = DATA_DIR / "redteam.txt"
    if not redteam.exists():
        print(f"  ERROR: redteam.txt not found at {redteam}")
        ok = False
    else:
        print(f"  ✓ redteam.txt: {redteam.stat().st_size:,} bytes")

    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local",       action="store_true",
                        help="Use local Spark/no-cluster mode")
    parser.add_argument("--skip-kafka",  action="store_true",
                        help="Skip Kafka producer step")
    parser.add_argument("--skip-spark",  action="store_true",
                        help="Skip Spark streaming step")
    parser.add_argument("--skip-neo4j", action="store_true",
                        help="Skip Neo4j export")
    parser.add_argument("--skip-train",  action="store_true",
                        help="Skip model training")
    parser.add_argument("--model",       default="a1",
                        choices=["a1", "a2", "a3", "all"])
    parser.add_argument("--delta",       default="all",
                        choices=["1", "6", "24", "all"])
    args = parser.parse_args()

    py = sys.executable

    if not check_prerequisites():
        sys.exit(1)

    steps = []

    # Step 1: Parse labels
    steps.append(([py, "pipeline/01_parse_labels.py"],
                   "01: Parse red-team labels"))

    # Step 2: ETL
    agg_parquet = PARQUET_DIR / "flows" / "flows_agg.parquet"
    if not agg_parquet.exists():
        steps.append(([py, "pipeline/02_etl_flows.py"],
                       "02: ETL flows.txt → Parquet"))
    else:
        print(f"[Pipeline] Step 02 skipped: {agg_parquet} already exists")

    # Step 3: Kafka (optional)
    if not args.skip_kafka:
        steps.append(([py, "pipeline/03_kafka_producer.py",
                       "--dry-run"],
                       "03: Kafka producer dry-run validation"))

    # Step 4: Spark streaming (optional)
    if not args.skip_spark:
        cmd = [py, "pipeline/04_spark_streaming.py", "--parquet-fallback"]
        if args.local:
            cmd.append("--local")
        steps.append((cmd, "04: Spark Structured Streaming (parquet fallback)"))

    # Step 5: GraphFrames candidates
    cands_path = DATA_OUT / "candidates_all.parquet"
    if not cands_path.exists():
        cmd = [py, "pipeline/05_graphframes_candidates.py", "--pandas-only"]
        if not args.local:
            cmd = [py, "pipeline/05_graphframes_candidates.py", "--local"]
        steps.append((cmd, "05: GraphFrames candidate sets"))
    else:
        print(f"[Pipeline] Step 05 skipped: candidates_all.parquet already exists")

    # Step 6: Train DHAP-Net
    if not args.skip_train:
        steps.append(([py, "train.py",
                       f"--model={args.model}",
                       f"--delta={args.delta}"],
                       "06: Train DHAP-Net"))

    # Step 7: MLlib baseline
    steps.append(([py, "pipeline/07_mllib_baseline.py",
                   "--pandas-only" if args.skip_spark else "--local"],
                   "07: Spark MLlib Random Forest baseline"))

    # Step 8: Evaluate
    steps.append(([py, "evaluate.py"], "08: Evaluation + tables"))

    # Step 9: Neo4j (optional)
    if not args.skip_neo4j:
        steps.append(([py, "pipeline/06_neo4j_export.py"],
                       "09: Neo4j export"))

    # Step 10: Dashboard
    steps.append(([py, "viz/build_dashboard.py"], "10: Plotly dashboard"))

    # Step 11: Tests
    steps.append(([py, "-m", "pytest", "tests/", "-v", "--tb=short"],
                   "11: Test suite"))

    # Execute
    failed = []
    for cmd, name in steps:
        ok = run(cmd, name)
        if not ok:
            failed.append(name)

    print(f"\n{'='*60}")
    print("[Pipeline] Summary")
    print(f"{'='*60}")
    total = len(steps)
    passed = total - len(failed)
    print(f"  Passed: {passed}/{total}")
    if failed:
        print("  Failed steps:")
        for f in failed:
            print(f"    ✗ {f}")
    else:
        print("  All steps completed successfully!")
    print(f"\n[Pipeline] View results:")
    print(f"  Dashboard: reports/figures/")
    print(f"  Tables:    reports/tables/")
    print(f"  Neo4j:     http://localhost:7474")
    print(f"  Spark UI:  http://localhost:8080")
    print(f"  HDFS UI:   http://localhost:9870")


if __name__ == "__main__":
    main()
