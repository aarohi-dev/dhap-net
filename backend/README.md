# DHAP-NET Backend API Adapter

FastAPI server adapter providing a REST API layer that serves existing DHAP-NET pre-computed pipeline results and datasets to the React frontend dashboard.

> **Important Note:** This backend adapter does **not** alter, replace, or re-run any core ML research algorithms (`train.py`, `evaluate.py`, `pipeline/`, `models/`, or `configs/`). It acts purely as a non-intrusive presentation and query adapter for the pre-computed outputs and artifacts produced by the research pipeline.

---

## Architecture & Data Flow

- **Pre-computed Artifacts & Datasets**:
  - `reports/data/candidates_all.parquet`: Features and labels for candidate propagation hosts (in/out degree, bytes, hop distance, labels).
  - `reports/data/preds_{model}_delta{1,6,24}h_seed{42,123,2024}.json`: Probability predictions and ground truth labels for models (A1 DHAP-Net, A2 TGN-TA, A3 DM-STG-AD).
  - `reports/tables/final_results.csv`: Comprehensive baseline and model comparison metrics (AP, ROC-AUC, P@k, R@k, Brier score).
  - `reports/tables/training_results.json`: Training history and per-epoch metrics.
  - `reports/slice_window.json`: Dataset window bounds and red-team event coverage counts.
  - `reports/throughput.json`: Streaming ingestion throughput benchmarks.
  - `reports/coverage_ceiling.json`: Multi-hop reachability coverage bounds.
  - `reports/data/redteam_per_day.csv`: Daily compromised activity counts.
  - `data/parquet/flows/flows_agg.parquet`: Aggregated network flow records between source and destination entities.

- **Graceful Fallbacks**:
  - Parquet reading prioritizes `pyarrow`, seamlessly falling back to `fastparquet`. If native parquet libraries are blocked in the environment, clean synthetic LANL-format fixtures are returned with metadata indicating fixture mode.
  - Missing or empty files return structured fallbacks without crashing the server.

---

## Endpoints Reference

### Health & System Status
- `GET /health` — Simple healthcheck endpoint returning server status and UTC timestamp.
- `GET /api/status` — Returns simulated pipeline infrastructure health (Kafka, Spark, Neo4j, storage, demo mode indicator).
- `GET /api/slice_window` — Returns temporal slice window information from `reports/slice_window.json`.
- `GET /api/throughput` — Returns streaming ingestion throughput metrics from `reports/throughput.json`.
- `GET /api/coverage_ceiling` — Returns hop coverage ceiling bounds from `reports/coverage_ceiling.json`.

### Network Flows & Threat Activity
- `GET /api/flows?limit=200&src=&dst=&protocol=` — Returns aggregated network flow records filtered by source, destination, or protocol.
- `GET /api/redteam` — Returns daily red-team event records from `reports/data/redteam_per_day.csv`.

### Candidates & Model Predictions
- `GET /api/candidates?delta=21600&limit=100` — Returns candidate host evaluation instances with graph features.
- `GET /api/predictions?model=a1&delta=6&seed=42` — Returns top ranked host predictions merged with candidate metadata.
- `GET /api/predictions/comparison` — Returns comparative performance across models and baselines from `reports/tables/final_results.csv`.

### Attack Graph & Propagation Topology
- `GET /api/graph?limit=100` — Generates a graph containing compromised nodes (`confirmed_compromised`), predicted risk nodes (`predicted_risk`), observed communication edges (`COMMUNICATES_WITH`), and simulated propagation paths (`SIMULATED_PROPAGATION`, marked with `simulated: true`).
- `GET /api/graph/entity/{host_id}` — Returns the 1-hop sub-graph centered on a specific host.

### Entity Profiling & Search
- `GET /api/entities?search=C10` — Search and auto-complete host identifiers.
- `GET /api/entity/{host_id}` — Returns an individual entity's full profile, network degree, historical predictions across models, and connected hosts.

### Analytics & Training
- `GET /api/training_results` — Returns full model training curves and epoch metrics.
- `GET /api/model_metrics` — Returns model comparison metrics grouped by model and delta window.

---

## Running the Server

### Prerequisites
Install dependencies:
```bash
pip install -r backend/requirements.txt
```
*(Or manually: `pip install fastapi uvicorn pandas numpy python-multipart`)*

### Starting the Server
From repository root:
```bash
cd e:\GitHub\dhap-net
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Alternatively, on Windows run:
```cmd
backend\start.bat
```

Interactive API documentation (Swagger UI) is available at:
[http://localhost:8000/docs](http://localhost:8000/docs)
