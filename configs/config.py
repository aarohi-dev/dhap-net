"""
Central configuration for the DHAP-Net / LANL project.
Edit values here; everything else imports from this file.

Dataset: reports/data/flows.txt  (LANL netflow, 130M records, ~942 MB)
Schema : time,duration,src,src_port,dst,dst_port,protocol,packets,bytes
"""

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parent.parent
DATA_DIR    = ROOT / "data"   / "raw"
PARQUET_DIR = ROOT / "data"   / "parquet"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
TABLES_DIR  = REPORTS_DIR / "tables"
DATA_OUT    = REPORTS_DIR / "data"
MODELS_DIR  = ROOT / "checkpoints"

# ── PRIMARY DATASET (immutable) ───────────────────────────────────────────────
FLOWS_TXT   = ROOT / "reports" / "data" / "flows.txt"   # 942 MB, 130M lines

for d in [DATA_DIR, PARQUET_DIR, REPORTS_DIR, FIGURES_DIR,
          TABLES_DIR, DATA_OUT, MODELS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Download budget ───────────────────────────────────────────────────────────
DOWNLOAD_BUDGET_GB = 2.0
DOWNLOAD_LEDGER    = REPORTS_DIR / "download_ledger.csv"

# ── HuggingFace repo (kept for redteam.txt reference only; data already local)
HF_REPO   = "Taqui/lanl-cyber-datasets"
HF_PREFIX = "lanl-2015"

# ── flows.txt schema ─────────────────────────────────────────────────────────
# Columns:  time, duration, src, src_port, dst, dst_port, protocol, packets, bytes
# time      : int  – seconds since capture start (epoch-relative)
# duration  : int  – flow duration in seconds
# src       : str  – anonymised source host  e.g. "C1065", "U620"
# src_port  : str  – source port or service name e.g. "389", "N10451"
# dst       : str  – anonymised destination host
# dst_port  : str  – destination port or service name
# protocol  : int  – IP protocol number (6=TCP, 17=UDP, 1=ICMP)
# packets   : int  – packet count
# bytes     : int  – byte count
FLOWS_COLS = ["time","duration","src","src_port",
              "dst","dst_port","protocol","packets","bytes_val"]

# ── Redteam labels ────────────────────────────────────────────────────────────
# Format:  time, user, src, dst
# These are confirmed red-team authentication events from the LANL dataset.
REDTEAM_TXT = DATA_DIR / "redteam.txt"

# ── Time-slice (filled in by pipeline/01_parse_labels.py) ────────────────────
T_START: int = 0
T_END:   int = 0
LEADN_DAYS   = 2    # warm-up days before first red-team event

# ── Graph / model hyperparams ─────────────────────────────────────────────────
K_HOPS      = 2
DELTAS      = [3600, 6*3600, 24*3600]   # Δ seconds: 1h, 6h, 24h
WINDOW_S    = 24*3600
MICRO_BATCH = 3600   # seconds per streaming micro-batch

# ── Model dims ────────────────────────────────────────────────────────────────
D_HIDDEN      = 64
D_TIME        = 16
N_HEADS       = 4
TCN_DILATIONS = [1, 3, 5]
N_GRU_LAYERS  = 1
N_SAMPLES_TRAIN = 200
N_SAMPLES_EVAL  = 1000

# ── Training ─────────────────────────────────────────────────────────────────
SEEDS        = [42, 123, 2024]
EPOCHS       = 30
LR           = 1e-3
BATCH_SIZE   = 256
EARLY_STOP   = 5
NEG_RATIO    = 5

# ── Loss weights ─────────────────────────────────────────────────────────────
ALPHA = 0.0   # attack-type loss (disabled)
BETA  = 0.5   # BPD ELBO
GAMMA = 0.1   # KL regularisation

# ── Baselines ─────────────────────────────────────────────────────────────────
RF_N_TREES   = 200
LGBM_TRIALS  = 30
LGBM_LEAVES  = 63

# ── Evaluation ────────────────────────────────────────────────────────────────
TOP_K      = [5, 10, 50]
CI_NOMINAL = 0.90

# ── Spark ─────────────────────────────────────────────────────────────────────
SPARK_MASTER             = os.environ.get("SPARK_MASTER", "spark://localhost:7077")
SPARK_DRIVER_MEMORY      = "4g"
SPARK_EXECUTOR_MEMORY    = "4g"
SPARK_SHUFFLE_PARTS      = 16
SPARK_MAX_FILES_TRIG     = 1
SPARK_CHECKPOINT_DIR     = str(ROOT / "data" / "spark_checkpoints")

# ── Kafka ─────────────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP         = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
KAFKA_TOPIC_FLOWS       = "dhapnet.flows"
KAFKA_TOPIC_PREDS       = "dhapnet.predictions"
KAFKA_GROUP_ID          = "dhapnet-spark-consumer"
KAFKA_REPLAY_BATCH_SIZE = 1000   # records per Kafka publish call

# ── HDFS ──────────────────────────────────────────────────────────────────────
HDFS_NAMENODE          = os.environ.get("HDFS_NAMENODE", "hdfs://localhost:9000")
HDFS_FLOWS_PATH        = "/dhapnet/flows"
HDFS_GRAPHS_PATH       = "/dhapnet/graphs"
HDFS_PREDICTIONS_PATH  = "/dhapnet/predictions"
HDFS_CHECKPOINTS_PATH  = "/dhapnet/checkpoints"

# ── Neo4j ─────────────────────────────────────────────────────────────────────
NEO4J_URI      = os.environ.get("NEO4J_URI",  "bolt://localhost:7687")
NEO4J_USER     = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "dhapnet2024")

# ── Misc ──────────────────────────────────────────────────────────────────────
DEVICE    = "cpu"
LOG_LEVEL = "INFO"
