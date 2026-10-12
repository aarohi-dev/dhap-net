"""
pipeline/03_kafka_producer.py
──────────────────────────────
Kafka Producer: reads flows.txt and publishes records to the
'dhapnet.flows' topic in chronological order.

This is a HISTORICAL REPLAY — not live production data.
Each record is a JSON-encoded flow event.

Usage:
    # Start Docker services first:
    #   docker compose up -d kafka
    python pipeline/03_kafka_producer.py [--max-records N] [--speed-factor F]

Flags:
    --max-records N    Stop after N records (0 = all)
    --speed-factor F   Replay speed multiplier (1.0 = real-time, 0 = max speed)
    --dry-run          Parse and count without sending to Kafka

Topic schema (JSON per message):
    {
        "time":      int,    # seconds from capture start
        "duration":  int,
        "src":       str,
        "src_port":  str,
        "dst":       str,
        "dst_port":  str,
        "protocol":  int,
        "packets":   int,
        "bytes":     int,
        "_replay":   true    # marker: this is historical data replay
    }
"""

import sys, json, time, argparse, io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs.config import (
    FLOWS_TXT, KAFKA_BOOTSTRAP, KAFKA_TOPIC_FLOWS, KAFKA_REPLAY_BATCH_SIZE
)


def get_producer():
    """Return a kafka-python KafkaProducer, or raise ImportError with advice."""
    try:
        from kafka import KafkaProducer
        return KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            batch_size=16384,
            linger_ms=10,
            compression_type="gzip",
            retries=3,
            request_timeout_ms=30000,
        )
    except ImportError:
        raise ImportError(
            "kafka-python not installed. Run: pip install kafka-python"
        )


def parse_line(line: str) -> dict | None:
    parts = line.strip().split(",")
    if len(parts) < 9:
        return None
    try:
        return {
            "time":     int(parts[0]),
            "duration": int(parts[1]),
            "src":      parts[2],
            "src_port": parts[3],
            "dst":      parts[4],
            "dst_port": parts[5],
            "protocol": int(parts[6]),
            "packets":  int(parts[7]),
            "bytes":    int(parts[8]),
            "_replay":  True,
        }
    except (ValueError, IndexError):
        return None


def produce(max_records: int = 0, speed_factor: float = 0.0,
            dry_run: bool = False):
    """
    Read flows.txt and publish to Kafka.
    speed_factor=0 --> as fast as possible (default for ETL replay).
    speed_factor=1 --> simulate real-time (1 second per dataset-second).
    """
    print(f"\n[Producer] HISTORICAL REPLAY — not live data")
    print(f"[Producer] Source : {FLOWS_TXT}")
    print(f"[Producer] Topic  : {KAFKA_TOPIC_FLOWS}")
    print(f"[Producer] Broker : {KAFKA_BOOTSTRAP}")
    print(f"[Producer] Dry-run: {dry_run}")

    producer = None
    if not dry_run:
        try:
            producer = get_producer()
            print("[Producer] Kafka producer connected.")
        except Exception as e:
            print(f"[Producer] ERROR: {e}")
            print("[Producer] Falling back to dry-run mode.")
            dry_run = True

    sent       = 0
    bad        = 0
    t0_wall    = time.time()
    prev_ts    = None     # previous record timestamp

    with open(FLOWS_TXT, "r", encoding="utf-8", errors="replace") as f:
        batch = []
        for raw_line in f:
            rec = parse_line(raw_line)
            if rec is None:
                bad += 1
                continue

            # Speed control (real-time replay)
            if speed_factor > 0 and prev_ts is not None:
                dt_data = rec["time"] - prev_ts
                if dt_data > 0:
                    time.sleep(dt_data / speed_factor)
            prev_ts = rec["time"]

            batch.append(rec)
            if len(batch) >= KAFKA_REPLAY_BATCH_SIZE:
                if not dry_run and producer:
                    for r in batch:
                        producer.send(KAFKA_TOPIC_FLOWS,
                                      value=r,
                                      key=str(r["src"]).encode())
                    producer.flush()
                sent += len(batch)
                batch = []

                if sent % 100_000 == 0:
                    elapsed = time.time() - t0_wall
                    rate = sent / elapsed
                    print(f"\r  sent={sent:,}  bad={bad:,}  "
                          f"{rate:,.0f} rec/s  {elapsed:.0f}s", end="", flush=True)

            if max_records > 0 and sent >= max_records:
                break

        # Flush remaining
        if batch and not dry_run and producer:
            for r in batch:
                producer.send(KAFKA_TOPIC_FLOWS, value=r,
                              key=str(r["src"]).encode())
            producer.flush()
            sent += len(batch)

    elapsed = time.time() - t0_wall
    print(f"\n[Producer] {'DRY-RUN ' if dry_run else ''}Complete")
    print(f"  Records sent  : {sent:,}")
    print(f"  Malformed     : {bad:,}")
    print(f"  Elapsed       : {elapsed:.1f}s")
    print(f"  Rate          : {sent/max(elapsed,1):,.0f} rec/s")

    if producer:
        producer.close()


def create_topic():
    """Create the Kafka topic if it does not exist."""
    try:
        from kafka.admin import KafkaAdminClient, NewTopic
        admin = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP)
        existing = admin.list_topics()
        if KAFKA_TOPIC_FLOWS not in existing:
            admin.create_topics([
                NewTopic(name=KAFKA_TOPIC_FLOWS,
                         num_partitions=4,
                         replication_factor=1)
            ])
            print(f"[Producer] Created topic: {KAFKA_TOPIC_FLOWS}")
        else:
            print(f"[Producer] Topic already exists: {KAFKA_TOPIC_FLOWS}")
        admin.close()
    except Exception as e:
        print(f"[Producer] Topic creation warning: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DHAP-Net Kafka flow producer")
    parser.add_argument("--max-records", type=int, default=0,
                        help="Stop after N records (0 = all)")
    parser.add_argument("--speed-factor", type=float, default=0.0,
                        help="Replay speed multiplier (0=max speed, 1=real-time)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse without sending to Kafka")
    args = parser.parse_args()

    if not args.dry_run:
        create_topic()

    produce(max_records=args.max_records,
            speed_factor=args.speed_factor,
            dry_run=args.dry_run)
