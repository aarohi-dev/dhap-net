# DHAP-Net: Dynamic Heterogeneous Attack-Propagation Network

Research implementation of DHAP-Net on the LANL Unified Host and Network Dataset.

> **Dataset:** `reports/data/flows.txt` — the sole permitted research dataset (LANL netflow, ~942 MB, 130M records).  
> **Labels:** `data/raw/redteam.txt` — 749 confirmed red-team authentication events, 301 compromised hosts.

---

## Architecture

```
flows.txt (942 MB)
    │
    ▼
Apache Kafka ─────────────────── Historical replay (labelled: not live data)
    │  Topic: dhapnet.flows
    ▼
Apache Spark Structured Streaming
    │  Schema enforcement · Deduplication · Checkpointing
    ▼
GraphFrames (on Spark)  ──────── K-hop BFS · Graph snapshots · In/out degrees
    │
    ▼
HDFS (/dhapnet/flows, /dhapnet/graphs, /dhapnet/predictions)
    │
    ▼
PyTorch Geometric Temporal / DHAP-Net
    │   ┌─ HRE   : Heterogeneous Relation Encoder (Time2Vec, per-relation W_r)
    │   ├─ ST-DTE: Spatio-Temporal Dual Encoder
    │   │           - Dilated TCN (d=1,3,5)   short-term burst detector
    │   │           - Bidirectional GRU        long-term temporal detector
    │   │           - Transformer Attention    informative-event selection
    │   └─ BPD   : Bayesian Propagation-Diffusion Layer (MANDATORY)
    │               - LogNormal posterior per edge rate λ
    │               - ELBO training objective
    │               - Gillespie Monte-Carlo rollout (M=1000 eval samples)
    │               - P̂(v,H) = (1/M) Σ 1[T_v^(m) ≤ H]
    ▼
Spark MLlib Random Forest ─────── Baseline comparison (same chronological split)
    │
    ▼
Neo4j (Browser / Bloom) ──────── Host graph · Confirmed compromises · SIMULATED paths
    │
    ▼
Plotly ───────────────────────── Interactive dashboards (reports/figures/)
```

---

## Dataset Audit

| Property | Value |
|---|---|
| File | `reports/data/flows.txt` |
| Size | ~942 MB (observed) |
| Records | 129,977,413 lines |
| Schema | `time,duration,src,src_port,dst,dst_port,protocol,packets,bytes` |
| Header | None |
| Delimiter | Comma |
| time | int — seconds since capture start |
| src / dst | Anonymised host IDs (e.g. C1065, U620) |
| src_port / dst_port | Port number or service alias (e.g. N10451, 389) |
| protocol | 6=TCP, 17=UDP, 1=ICMP |
| Timestamps | Present — chronological split enforced |
| Attack labels | `data/raw/redteam.txt` — 749 confirmed red-team events |
| Compromised hosts | 301 (dst) + 4 footholds (src only) |
| Slice window | Day 0 → Day 29.6 (t_start=0, t_end=2,560,647 s) |

### Research-integrity notes

- Network flows ≠ confirmed compromise. The BPD layer explicitly models *propagation probability* not *ground-truth compromise status*.
- `label=1` means a host is reached by a confirmed red-team event within Δ seconds — derived from `redteam.txt` only.
- No synthetic labels are generated. No external datasets are used.
- Monte-Carlo CI reflects sampling variance over BPD rollouts, not calibrated compromise uncertainty.

---

## Setup

### 1. Prerequisites

| Component | Requirement |
|---|---|
| Python | 3.10 – 3.14 |
| Java | **17** (Spark 3.5 supports Java 8/11/17; **NOT 26**) |
| Docker Desktop | For Kafka, Spark, HDFS, Neo4j |

> ⚠️ **Java version**: The system has Java 26, which is **incompatible with PySpark 3.5**.  
> Install [Temurin JDK 17](https://adoptium.net/) and set `JAVA_HOME` before running Spark.

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

Key packages:
- `kafka-python>=2.0.2` — Kafka producer/consumer
- `neo4j>=5.18.0` — Neo4j driver
- `pyspark==3.5.1` — Spark + MLlib + Structured Streaming
- `torch-geometric-temporal>=0.54.0` — Temporal GNN
- `plotly>=5.18` — Interactive dashboards

### 3. Start infrastructure services

```bash
# Start all services (Kafka, Spark, HDFS, Neo4j)
docker compose up -d

# Verify services are healthy
docker compose ps
```

Service URLs:
| Service | URL |
|---|---|
| Kafka | `localhost:9092` |
| Spark Master UI | `http://localhost:8080` |
| HDFS NameNode UI | `http://localhost:9870` |
| Neo4j Browser | `http://localhost:7474` (user: neo4j, pass: dhapnet2024) |

---

## Execution Order

### Step 1: Parse red-team labels
```bash
python pipeline/01_parse_labels.py
```
Outputs: `data/raw/redteam_labels.csv`, `reports/slice_window.json`

### Step 2: ETL — flows.txt → Parquet
```bash
python pipeline/02_etl_flows.py
```
Outputs: `data/parquet/flows/flows_agg.parquet` (~50–80 MB aggregated)  
Runtime: ~10–20 min on 942 MB file

### Step 3: Kafka producer (historical replay)
```bash
# Dry-run validation (no Kafka needed):
python pipeline/03_kafka_producer.py --dry-run

# Full replay to Kafka (requires Kafka running):
python pipeline/03_kafka_producer.py --max-records 1000000
```

### Step 4: Spark Structured Streaming
```bash
# Local parquet-fallback mode (no Kafka needed):
python pipeline/04_spark_streaming.py --parquet-fallback --local

# Full cluster mode (requires Spark cluster + Kafka):
spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,\
             graphframes:graphframes:0.8.4-spark3.5-s_2.12 \
  pipeline/04_spark_streaming.py
```

### Step 5: GraphFrames candidate sets
```bash
# Pure pandas mode (no Spark needed):
python pipeline/05_graphframes_candidates.py --pandas-only

# Spark + GraphFrames mode:
python pipeline/05_graphframes_candidates.py --local
```
Outputs: `reports/data/{train,val,test,candidates_all}.parquet`

### Step 6: Train DHAP-Net
```bash
# Train A1 (DHAP-Net) for all deltas and seeds:
python train.py --model a1 --delta all

# Train all models:
python train.py --model all --delta all
```
Outputs: `checkpoints/*.pt`, `reports/tables/training_results.json`

### Step 7: Spark MLlib baseline
```bash
python pipeline/07_mllib_baseline.py --local
```

### Step 8: Evaluate
```bash
python evaluate.py
```
Outputs: `reports/tables/final_results.csv`, `reports/tables/calibration.csv`

### Step 9: Neo4j export
```bash
# Requires Neo4j running: docker compose up -d neo4j
python pipeline/06_neo4j_export.py
```

### Step 10: Plotly dashboard
```bash
python viz/build_dashboard.py
# Open reports/figures/*.html in browser
```

### All-in-one runner
```bash
# Local mode (no cluster):
python run_pipeline.py --local --skip-kafka --skip-neo4j

# Full mode (all services):
docker compose up -d
python run_pipeline.py
```

---

## Testing

```bash
# Run all tests:
python -m pytest tests/ -v --tb=short

# Run only unit tests (no services needed):
python -m pytest tests/ -v -k "not TestIntegration"

# Run specific test class:
python -m pytest tests/test_pipeline.py::TestBPD -v
```

Test coverage:
1. `TestFlowsParsing` — Dataset parsing, malformed records, no-fabrication checks
2. `TestGraphConstruction` — Vertices, edges, directed graph properties
3. `TestTimestamps` — No future leakage, chronological split
4. `TestKHop` — 1-hop, 2-hop, 3-hop BFS; disconnected nodes; empty seeds
5. `TestTemporalEncoder` — Time2Vec, DilatedTCN, STDTE, HRE forward passes
6. `TestBPD` — λ > 0, σ > 0, P ∈ [0,1], reproducibility, CI labelling, ELBO
7. `TestDHAPNetForward` — Empty batch, full forward, memory update
8. `TestCandidateLabels` — Binary labels, derived from redteam only
9. `TestKafkaProducer` — parse_line, dry-run
10. `TestMetrics` — AP, ROC-AUC, P@K edge cases
11. `TestIntegration` — Parquet schema, slice_window.json, service connections

---

## DHAP-Net Model

### Heterogeneous Relation Encoder (HRE)
```
m_{u→v}^r(t) = W_r · [h_u ‖ x_uv ‖ TE(t − t_u)]
```
- Per-relation weight matrix `W_r` (flows.txt has 1 relation type: `COMMUNICATES_WITH`)
- Time2Vec encoding of temporal gap
- Extensible: add relation types as data supports them

### Spatio-Temporal Dual Encoder (ST-DTE)
```
Short-term  : DilatedTCN(d=1,3,5)  — burst detection
Long-term   : BiGRU                 — sustained activity patterns  
Attention   : TransformerEncoder    — informative event selection
Fused       : Linear([TCN ‖ BiGRU ‖ Transformer]) → h_v(t)
```

### Bayesian Propagation-Diffusion (BPD) — Core Contribution
```
Edge rate prior:    λ_{ij} ~ LogNormal(μ_{ij}, σ²_{ij})
Rate estimation:    [μ, σ] = MLP([h_i ‖ h_j ‖ TE(t − T_i)])
Training objective: ELBO = E_q[log p(data|λ)] − KL(q ‖ prior) + β·ELBO + γ·KL
Propagation delay:  T_j^(m) ~ Exp(Σ_i λ_{ij}^(m))    [Gillespie approximation]
Probability:        P̂(v, H) = (1/M) Σ_{m=1}^M 1[T_v^(m) ≤ H]
```

**Assumptions (explicit):**
- Propagation modelled as a Poisson process — real attack propagation may not be Poisson
- Edge eligibility: any communication edge where src is compromised at time t
- λ estimated from communication features; not from observed propagation rate (no ground truth for propagation rate)
- MC interval reflects rollout variance, not parameter uncertainty

---

## Java Compatibility Warning

```
Current Java: 26.0.1   ← INCOMPATIBLE with PySpark 3.5
Required:     Java 17   ← Install Temurin JDK 17

Steps:
1. Download: https://adoptium.net/temurin/releases/?version=17
2. Install to e.g. C:\Program Files\Eclipse Adoptium\jdk-17.x.x
3. Set JAVA_HOME: $env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.x.x"
4. In docker compose services, Java is already 8 (via bitnami/spark image) — no issue there.
```

Use `docker compose` to run Spark without local Java compatibility issues.

---

## File Structure

```
dhap-net/
├── docker-compose.yml          ← Full infrastructure stack
├── run_pipeline.py             ← Master orchestrator
├── train.py                    ← DHAP-Net training loop
├── evaluate.py                 ← Evaluation + comparison tables
├── requirements.txt
├── .gitignore
│
├── configs/
│   └── config.py               ← Central config (paths, hyperparams, service URLs)
│
├── pipeline/
│   ├── 01_parse_labels.py      ← Parse redteam.txt → labels + slice window
│   ├── 02_etl_flows.py         ← ETL: flows.txt → Parquet (942 MB → ~50 MB)
│   ├── 03_kafka_producer.py    ← Kafka historical replay producer
│   ├── 04_spark_streaming.py   ← Spark Structured Streaming + GraphFrames
│   ├── 05_graphframes_candidates.py  ← K-hop BFS candidate sets
│   ├── 06_neo4j_export.py      ← Neo4j graph + predictions export
│   ├── 07_mllib_baseline.py    ← Spark MLlib Random Forest baseline
│   ├── graph_ops.py            ← Alias for importable graph functions
│   └── kafka_producer.py       ← Alias for importable producer functions
│
├── models/
│   ├── a1_dhapnet.py           ← DHAP-Net (HRE + ST-DTE + BPD)
│   ├── a2_tgne_ta.py           ← TGN-TA baseline
│   ├── a3_dmstg_ad.py          ← DMSTG-AD baseline
│   ├── baselines.py            ← Additional baselines
│   └── shared.py               ← Time2Vec, NodeMemory, DilatedTCN, metrics
│
├── viz/
│   ├── build_dashboard.py      ← Plotly dashboard (all real data)
│   ├── eda_figs.py
│   ├── graph_view.py
│   └── result_figs.py
│
├── tests/
│   ├── test_pipeline.py        ← 20-category test suite
│   └── smoke_etl.py
│
├── data/
│   ├── raw/
│   │   ├── redteam.txt         ← LANL red-team labels (749 events, tracked in Git)
│   │   └── redteam_labels.csv  ← Parsed labels (generated)
│   └── parquet/                ← ETL output (gitignored)
│
└── reports/
    ├── data/
    │   └── flows.txt           ← PRIMARY DATASET (942 MB, tracked in Git)
    ├── figures/                ← Plotly HTML (gitignored)
    └── tables/                 ← Results (gitignored)
```

---

## Credentials

| Service | User | Password |
|---|---|---|
| Neo4j | neo4j | dhapnet2024 |
| HDFS | — | — |
| Kafka | — | — |

> **Never commit passwords.** For production use, set via environment variables:
> `NEO4J_PASSWORD`, `KAFKA_BOOTSTRAP`, `HDFS_NAMENODE`, `NEO4J_URI`.

---

## Known Limitations

1. **Java 26 incompatible with PySpark 3.5** — Use Docker or downgrade to Java 17.
2. **No observed propagation rate** — BPD λ is estimated from communication features, not confirmed propagation events. CI is sampling variance, not epistemic uncertainty over λ.
3. **Single edge type** — flows.txt supports only `COMMUNICATES_WITH`. HRE is designed for multiple relation types and will benefit from richer data.
4. **flows.txt is 942 MB** — Not `flows_slice.txt` (1.7 GB, excluded). The full flows dataset provides 130M records over 29.6 days.
5. **Kafka replay is historical** — Not live network collection. Clearly labelled `_replay: true` in every record.
