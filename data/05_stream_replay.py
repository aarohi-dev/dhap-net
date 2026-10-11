"""
Step 4 – Structured-Streaming replay (Spark emulated with pandas).
Replays the aggregated Parquet data in 1-hour micro-batches, in time order.
Yields (hour, batch_df) tuples.

A real PySpark Structured Streaming version would use:
  spark.readStream.schema(schema).parquet(path)
  .trigger(processingTime="1 hour")
This version uses pandas to replay the same Parquet in chronological order.

Run standalone for testing: python data/05_stream_replay.py
Import replay_stream() in training code.
"""

import sys, time
from pathlib import Path
from typing import Generator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configs.config import PARQUET_DIR, MICRO_BATCH

import pandas as pd
import pyarrow.parquet as pq

def replay_stream(
    source: str = "auth",
    yield_hour: bool = True,
) -> Generator[tuple[int, pd.DataFrame], None, None]:
    """
    Yield (hour_timestamp_s, micro_batch_df) in ascending time order.
    Each micro-batch covers exactly one hour of data.
    Maintains the streaming property: no future data leaks in.
    """
    parquet_path = PARQUET_DIR / source / f"{source}_agg.parquet"
    if not parquet_path.exists():
        raise FileNotFoundError(
            f"Parquet not found: {parquet_path}. Run 04_spark_etl.py first."
        )

    df = pd.read_parquet(str(parquet_path))
    df = df.sort_values("hour").reset_index(drop=True)

    hours = sorted(df["hour"].unique())
    print(f"[Stream] Replaying {source}: {len(hours)} micro-batches "
          f"(hours {hours[0]:,} → {hours[-1]:,})")

    for h in hours:
        batch = df[df["hour"] == h].copy()
        yield h * 3600, batch   # yield wall-clock second for the batch

    print(f"[Stream] Replay complete.")

# ── throughput benchmark ──────────────────────────────────────────────────────
def benchmark_replay():
    t0 = time.time()
    total_events = 0
    total_batches = 0
    for ts, batch in replay_stream("flows"):
        total_events += int(batch["n_flows"].sum() if "n_flows" in batch.columns
                           else batch.get("n_events", batch.iloc[:,5]).sum())
        total_batches += 1
    elapsed = time.time() - t0
    eps = total_events / elapsed if elapsed > 0 else 0
    print(f"\n[Benchmark] {total_batches} micro-batches, "
          f"{total_events:,} events in {elapsed:.2f}s → "
          f"{eps:,.0f} events/s, "
          f"{elapsed/total_batches*1000:.1f} ms/micro-batch")
    return {"events_per_sec": eps, "ms_per_batch": elapsed/total_batches*1000,
            "total_batches": total_batches, "elapsed_s": elapsed}

if __name__ == "__main__":
    results = benchmark_replay()
    import json
    from configs.config import REPORTS_DIR
    with open(REPORTS_DIR / "throughput.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[Stream] Throughput saved to reports/throughput.json")
