"""
Central configuration for the DHAP-Net / LANL project.
Edit values here; everything else imports from this file.
"""

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR   = ROOT / "data"   / "raw"
PARQUET_DIR= ROOT / "data"   / "parquet"
REPORTS_DIR= ROOT / "reports"
FIGURES_DIR= REPORTS_DIR / "figures"
TABLES_DIR = REPORTS_DIR / "tables"
DATA_OUT   = REPORTS_DIR / "data"
MODELS_DIR = ROOT / "checkpoints"

for d in [DATA_DIR, PARQUET_DIR, REPORTS_DIR, FIGURES_DIR, TABLES_DIR, DATA_OUT, MODELS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Download budget ───────────────────────────────────────────────────────────
DOWNLOAD_BUDGET_GB = 2.0          # hard ceiling
DOWNLOAD_LEDGER    = REPORTS_DIR / "download_ledger.csv"

# ── HuggingFace repo ─────────────────────────────────────────────────────────
HF_REPO   = "Taqui/lanl-cyber-datasets"
HF_PREFIX = "lanl-2015"

# ── Time-slice (filled in by 01_labels.py after reading redteam) ─────────────
# Defaults that will be overridden at runtime
T_START: int = 0        # seconds from capture start
T_END:   int = 0        # seconds from capture start
LEADN_DAYS = 2          # warm-up days before first red-team event

# ── Graph / model hyperparams ─────────────────────────────────────────────────
K_HOPS      = 2          # propagation hops
DELTAS      = [3600, 6*3600, 24*3600]   # Δ in seconds: 1h, 6h, 24h
WINDOW_S    = 24*3600    # trailing window for candidate graph (24 h)
MICRO_BATCH = 3600       # micro-batch size in seconds (1 h)

# ── Model dims ────────────────────────────────────────────────────────────────
D_HIDDEN    = 64
D_TIME      = 16         # Time2Vec output dim
N_HEADS     = 4
TCN_DILATIONS = [1, 3, 5]
N_GRU_LAYERS  = 1
N_SAMPLES_TRAIN = 200    # BPD Monte-Carlo samples during training
N_SAMPLES_EVAL  = 1000   # BPD Monte-Carlo samples at evaluation

# ── Training ─────────────────────────────────────────────────────────────────
SEEDS        = [42, 123, 2024]
EPOCHS       = 30
LR           = 1e-3
BATCH_SIZE   = 256
EARLY_STOP   = 5         # patience (epochs)
NEG_RATIO    = 5         # negative:positive ratio for training subsampling

# ── Loss weights ─────────────────────────────────────────────────────────────
ALPHA = 0.0   # attack-type loss (no labels → disabled)
BETA  = 0.5   # BPD ELBO
GAMMA = 0.1   # KL regularisation

# ── Baselines ─────────────────────────────────────────────────────────────────
RF_N_TREES   = 200
LGBM_TRIALS  = 30        # Optuna trials for LightGBM
LGBM_LEAVES  = 63

# ── Evaluation ────────────────────────────────────────────────────────────────
TOP_K   = [5, 10, 50]
CI_NOMINAL = 0.90        # nominal credible interval for coverage check

# ── Spark (local mode, Parquet stand-in for HDFS) ────────────────────────────
SPARK_DRIVER_MEMORY  = "4g"
SPARK_SHUFFLE_PARTS  = 16
SPARK_MAX_FILES_TRIG = 1   # Structured Streaming: files per trigger

# ── Misc ──────────────────────────────────────────────────────────────────────
DEVICE = "cpu"    # set to "cuda" if a GPU is available
LOG_LEVEL = "INFO"
