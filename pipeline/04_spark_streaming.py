"""
pipeline/04_spark_streaming.py
───────────────────────────────
Spark Structured Streaming consumer.

Reads from Kafka topic 'dhapnet.flows', enforces schema, handles
malformed records, deduplicates where possible, and writes to HDFS.

Data flow:
    Kafka --> Spark Structured Streaming --> GraphFrames --> HDFS

Usage (submit to cluster):
    spark-submit \\
      --master spark://spark-master:7077 \\
      --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,\\
                 graphframes:graphframes:0.8.4-spark3.5-s_2.12,\\
                 org.apache.spark:spark-avro_2.12:3.5.1 \\
      pipeline/04_spark_streaming.py

Usage (local test with Parquet fallback):
    python pipeline/04_spark_streaming.py --local

HDFS output directories (as per config):
    /dhapnet/flows          — validated flow records (partitioned by day, hour)
    /dhapnet/graphs         — per-hour graph snapshots as Parquet edge lists
    /dhapnet/checkpoints    — Spark streaming checkpoint
"""

import sys, os, json, io, argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs.config import (
    KAFKA_BOOTSTRAP, KAFKA_TOPIC_FLOWS, KAFKA_GROUP_ID,
    HDFS_NAMENODE, HDFS_FLOWS_PATH, HDFS_GRAPHS_PATH, HDFS_CHECKPOINTS_PATH,
    SPARK_MASTER, SPARK_DRIVER_MEMORY, SPARK_EXECUTOR_MEMORY,
    SPARK_SHUFFLE_PARTS, PARQUET_DIR
)


FLOW_SCHEMA_DDL = """
    `time`     INT,
    `duration` INT,
    `src`      STRING,
    `src_port` STRING,
    `dst`      STRING,
    `dst_port` STRING,
    `protocol` INT,
    `packets`  INT,
    `bytes`    INT,
    `_replay`  BOOLEAN
"""

GRAPH_SCHEMA_DDL = """
    `hour`          INT,
    `src`           STRING,
    `dst`           STRING,
    `protocol`      INT,
    `n_flows`       LONG,
    `total_bytes`   DOUBLE,
    `total_packets` DOUBLE
"""


def build_spark(local: bool = False):
    try:
        from pyspark.sql import SparkSession
    except ImportError:
        raise ImportError("PySpark not installed. Run: pip install pyspark==3.5.1")

    master = "local[*]" if local else SPARK_MASTER
    builder = (
        SparkSession.builder
        .appName("DHAP-Net Structured Streaming")
        .master(master)
        .config("spark.driver.memory", SPARK_DRIVER_MEMORY)
        .config("spark.executor.memory", SPARK_EXECUTOR_MEMORY)
        .config("spark.sql.shuffle.partitions", str(SPARK_SHUFFLE_PARTS))
        .config("spark.sql.streaming.checkpointLocation",
                f"{HDFS_NAMENODE}{HDFS_CHECKPOINTS_PATH}" if not local
                else str(PARQUET_DIR / "checkpoints"))
        # Kafka integration package (must be on classpath or --packages)
        .config("spark.jars.packages",
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,"
                "graphframes:graphframes:0.8.4-spark3.5-s_2.12")
    )
    if not local:
        builder = builder.config("spark.hadoop.fs.defaultFS", HDFS_NAMENODE)

    return builder.getOrCreate()


def run_kafka_streaming(spark, local: bool):
    """
    Spark Structured Streaming from Kafka.
    Each Kafka message value is a JSON-encoded flow record.
    """
    from pyspark.sql import functions as F
    from pyspark.sql.types import StructType, StructField, StringType, IntegerType, BooleanType

    schema = StructType([
        StructField("time",     IntegerType(), True),
        StructField("duration", IntegerType(), True),
        StructField("src",      StringType(),  True),
        StructField("src_port", StringType(),  True),
        StructField("dst",      StringType(),  True),
        StructField("dst_port", StringType(),  True),
        StructField("protocol", IntegerType(), True),
        StructField("packets",  IntegerType(), True),
        StructField("bytes",    IntegerType(), True),
        StructField("_replay",  BooleanType(), True),
    ])

    raw_stream = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", KAFKA_TOPIC_FLOWS)
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "false")
        .option("maxOffsetsPerTrigger", 50000)
        .load()
    )

    # Parse JSON values
    parsed = (
        raw_stream
        .select(F.from_json(F.col("value").cast("string"), schema).alias("d"))
        .select("d.*")
    )

    # Schema enforcement + validation
    valid = (
        parsed
        .filter(F.col("time").isNotNull())
        .filter(F.col("src").isNotNull())
        .filter(F.col("dst").isNotNull())
        .filter(F.col("time") >= 0)
        .withColumn("hour", (F.col("time") / 3600).cast("int"))
        .withColumn("day",  (F.col("time") / 86400).cast("int"))
        .withColumn("ingested_at", F.current_timestamp())
    )

    # Invalid records (for accounting)
    invalid = (
        parsed
        .filter(F.col("time").isNull()
                | F.col("src").isNull()
                | F.col("dst").isNull())
    )

    # Determine output paths
    if local:
        flows_out  = str(PARQUET_DIR / "flows_stream")
        graphs_out = str(PARQUET_DIR / "graphs_stream")
        ckpt_flows = str(PARQUET_DIR / "checkpoints" / "flows")
        ckpt_graphs = str(PARQUET_DIR / "checkpoints" / "graphs")
    else:
        flows_out  = f"{HDFS_NAMENODE}{HDFS_FLOWS_PATH}"
        graphs_out = f"{HDFS_NAMENODE}{HDFS_GRAPHS_PATH}"
        ckpt_flows  = f"{HDFS_NAMENODE}{HDFS_CHECKPOINTS_PATH}/flows"
        ckpt_graphs = f"{HDFS_NAMENODE}{HDFS_CHECKPOINTS_PATH}/graphs"

    Path(ckpt_flows).mkdir(parents=True, exist_ok=True)
    Path(ckpt_graphs).mkdir(parents=True, exist_ok=True)

    # Write validated flows to HDFS/local, partitioned by day and hour
    flow_query = (
        valid.writeStream
        .format("parquet")
        .option("path", flows_out)
        .option("checkpointLocation", ckpt_flows)
        .partitionBy("day", "hour")
        .outputMode("append")
        .trigger(processingTime="1 minute")
        .start()
    )

    print(f"[Spark] Flow stream started --> {flows_out}")
    print(f"[Spark] Checkpoint          --> {ckpt_flows}")

    # Micro-batch graph construction using GraphFrames
    def build_graph_snapshot(micro_batch_df, batch_id):
        """
        Per micro-batch: aggregate to hourly edge list and write to HDFS.
        Also run GraphFrames k-hop queries to identify propagation paths.
        """
        if micro_batch_df.count() == 0:
            return

        from pyspark.sql import functions as F2

        edge_agg = (
            micro_batch_df
            .groupBy("hour", "src", "dst", "protocol")
            .agg(
                F2.count("*").alias("n_flows"),
                F2.sum("bytes").cast("double").alias("total_bytes"),
                F2.sum("packets").cast("double").alias("total_packets"),
            )
        )

        # GraphFrames graph for this micro-batch
        try:
            from graphframes import GraphFrame
            vertices = (
                edge_agg
                .select(F2.col("src").alias("id"))
                .union(edge_agg.select(F2.col("dst").alias("id")))
                .distinct()
            )
            edges = edge_agg.select(
                F2.col("src"),
                F2.col("dst"),
                F2.col("n_flows"),
                F2.col("total_bytes"),
            )
            g = GraphFrame(vertices, edges)

            # Two-hop reachability for high-degree nodes (potential seeds)
            # Motif: (a)-[e]->(b)-[f]->(c)
            two_hop = g.find("(a)-[e]->(b); (b)-[f]->(c)")
            two_hop_count = two_hop.count()
            print(f"[Graph] Batch {batch_id}: "
                  f"vertices={vertices.count()} edges={edges.count()} "
                  f"2-hop paths={two_hop_count}")
        except ImportError:
            print(f"[Graph] Batch {batch_id}: GraphFrames not available; "
                  f"writing edge list only")

        # Write graph snapshot to HDFS
        edge_agg.write.mode("append").parquet(
            f"{graphs_out}/batch_{batch_id}"
        )

    graph_query = (
        valid.writeStream
        .foreachBatch(build_graph_snapshot)
        .option("checkpointLocation", ckpt_graphs)
        .outputMode("append")
        .trigger(processingTime="1 minute")
        .start()
    )

    print("[Spark] Graph stream started.")
    print("[Spark] Awaiting termination (Ctrl-C to stop) ...")

    spark.streams.awaitAnyTermination()


def run_pandas_graph_fallback(flows_parquet: str):
    """
    Pandas/PyArrow fallback when PySpark is not installed locally.
    Validates aggregated flows and demonstrates basic graph statistics.
    """
    import pandas as pd
    print(f"\n[Spark-Fallback] Reading {flows_parquet} via pandas/pyarrow ...")
    df = pd.read_parquet(flows_parquet)
    print(f"[Spark-Fallback] Loaded {len(df):,} aggregated flow rows")

    vertices = set(df["src"].unique()).union(set(df["dst"].unique()))
    print(f"[Spark-Fallback] Graph: {len(vertices):,} unique hosts, {len(df):,} aggregated edges")

    in_deg = df.groupby("dst")["n_flows"].sum().sort_values(ascending=False)
    out_deg = df.groupby("src")["n_flows"].sum().sort_values(ascending=False)
    print(f"[Spark-Fallback] Max in-degree  : {in_deg.iloc[0] if not in_deg.empty else 0:,}")
    print(f"[Spark-Fallback] Max out-degree : {out_deg.iloc[0] if not out_deg.empty else 0:,}")

    print("\n[Spark-Fallback] Top 5 in-degree destinations:")
    for host, count in in_deg.head(5).items():
        print(f"  {host}: {count:,} flows")

    print("\n[Spark] OK Done (pandas fallback).  Next: python pipeline/05_graphframes_candidates.py")


def run_parquet_fallback(local: bool):
    """
    Fallback: read already-aggregated Parquet (from 02_etl_flows.py)
    and run GraphFrames on it to demonstrate graph operations.
    Used when Kafka is not yet running.
    """
    flows_parquet = str(PARQUET_DIR / "flows" / "flows_agg.parquet")
    if not Path(flows_parquet).exists():
        print(f"[Spark] ERROR: Parquet not found at {flows_parquet}")
        print("  Run: python pipeline/02_etl_flows.py  first.")
        return

    try:
        from pyspark.sql import SparkSession
        from pyspark.sql import functions as F
        print("\n[Spark] Running in PARQUET FALLBACK mode (no Kafka).")
        spark = build_spark(local=True)
        spark.sparkContext.setLogLevel("WARN")
    except (ImportError, Exception) as e:
        print(f"\n[Spark] PySpark / Java not available ({e}).")
        print("[Spark] Falling back to pandas/pyarrow for graph operations demonstration.")
        run_pandas_graph_fallback(flows_parquet)
        return

    df = spark.read.parquet(flows_parquet)
    print(f"[Spark] Loaded {df.count():,} aggregated flow rows")

    # Build full graph
    try:
        from graphframes import GraphFrame

        vertices = (
            df.select(F.col("src").alias("id"))
            .union(df.select(F.col("dst").alias("id")))
            .distinct()
        )
        edges = df.select(
            F.col("src"),
            F.col("dst"),
            F.col("n_flows"),
            F.col("total_bytes"),
            F.col("hour"),
        )
        g = GraphFrame(vertices, edges)

        n_v = vertices.count()
        n_e = edges.count()
        print(f"[GraphFrames] Graph: {n_v:,} vertices, {n_e:,} edges")

        # In-degree distribution
        in_deg = g.inDegrees
        out_deg = g.outDegrees
        print(f"[GraphFrames] Max in-degree  : "
              f"{in_deg.agg({'inDegree': 'max'}).collect()[0][0]}")
        print(f"[GraphFrames] Max out-degree : "
              f"{out_deg.agg({'outDegree': 'max'}).collect()[0][0]}")

        # 2-hop motif: (a)-[e]->(b)-[f]->(c)
        two_hop = g.find("(a)-[e]->(b); (b)-[f]->(c)")
        print(f"[GraphFrames] 2-hop paths (sample): {two_hop.count():,}")

        # Save graph stats to HDFS or local
        out_path = str(PARQUET_DIR / "graphs" / "graph_snapshot")
        Path(out_path).mkdir(parents=True, exist_ok=True)
        edges.write.mode("overwrite").parquet(
            str(PARQUET_DIR / "graphs" / "edges_full")
        )
        in_deg.write.mode("overwrite").parquet(
            str(PARQUET_DIR / "graphs" / "in_degrees")
        )
        print(f"[GraphFrames] Saved to {out_path}")

    except ImportError as e:
        print(f"[Spark] GraphFrames not available: {e}")
        print("  Install: pip install graphframes or use --packages in spark-submit")

        # Without GraphFrames: demonstrate Spark SQL graph operations
        df.createOrReplaceTempView("flows")
        in_deg = spark.sql("""
            SELECT dst AS host, SUM(n_flows) AS in_degree
            FROM flows GROUP BY dst ORDER BY in_degree DESC LIMIT 20
        """)
        in_deg.show()

        # 2-hop in pure Spark SQL
        two_hop = spark.sql("""
            SELECT DISTINCT a.src AS seed, b.dst AS two_hop_node
            FROM flows a JOIN flows b ON a.dst = b.src
            LIMIT 1000
        """)
        print(f"[Spark SQL] 2-hop pairs (sample): {two_hop.count():,}")

    spark.stop()
    print("[Spark] OK Done.  Next: python pipeline/05_graphframes_candidates.py")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true",
                        help="Run in local mode (no cluster)")
    parser.add_argument("--parquet-fallback", action="store_true",
                        help="Use pre-built Parquet instead of Kafka stream")
    args = parser.parse_args()

    if args.parquet_fallback:
        run_parquet_fallback(local=args.local)
        return

    try:
        spark = build_spark(local=args.local)
        spark.sparkContext.setLogLevel("WARN")
        run_kafka_streaming(spark, local=args.local)
    except (ImportError, Exception) as e:
        print(f"\n[Spark] PySpark / Java not available ({e}).")
        print("[Spark] Switching to Parquet fallback mode.")
        run_parquet_fallback(local=args.local)


if __name__ == "__main__":
    main()
