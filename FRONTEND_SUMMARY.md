# DHAP-NET Frontend — Implementation Summary

## Overview

Complete, interactive frontend for the DHAP-NET (Dynamic Heterogeneous Attack-Propagation Network) cyber threat intelligence platform. Built as a React + TypeScript application that interfaces with the existing Python research backend.

**Stack:** React 19 · TypeScript 7 · Vite 8 · Tailwind CSS 4 · Lucide Icons · react-force-graph-2d · Plotly.js

> ⚠ **No existing backend Python files were modified.** The frontend communicates through a read-only FastAPI adapter that serves pre-computed pipeline outputs.

---

## Pages Implemented (8 total)

| Page | Route | Size | Description |
|------|-------|------|-------------|
| Overview Dashboard | `/overview` | 28.6 KB | System status, metrics, pipeline flow, live events, threat intelligence |
| Live Monitoring | `/monitoring` | 23.2 KB | Stream controls, health cards, event stream table, pipeline status |
| Attack Graph Explorer | `/graph` | 33.9 KB | Interactive force-graph with node/edge filtering, detail panel, Neo4j queries |
| Threat Predictions | `/predictions` | 28.5 KB | Model/delta/seed selectors, prediction table, model comparison |
| Anomaly Detection | `/anomalies` | 27.5 KB | Anomaly table with severity badges, detail panel, detection notes |
| Entity Investigation | `/entities` | 28.2 KB | Host search, entity profiles with tabs (overview/network/predictions/history) |
| Analytics | `/analytics` | 22.2 KB | Model performance charts, training loss, throughput, coverage ceiling |
| Reports | `/reports` | 15.3 KB | CSV exports, report generation, investigation history, visualization gallery |

## Components Created (14 total)

**Layout:** Sidebar.tsx (collapsible nav), TopBar.tsx (breadcrumb + demo banner), Layout.tsx (wrapper)

**UI:** MetricCard, StatusBadge, DataTable, FilterBar, SkeletonLoader, EmptyState, Toast, Tooltip

## Backend API Adapter

A minimal FastAPI server at `backend/main.py` that serves pre-computed pipeline outputs:

| Endpoint | Source |
|----------|--------|
| `GET /api/status` | Infrastructure status (all offline in demo) |
| `GET /api/flows` | `data/parquet/flows/flows_agg.parquet` |
| `GET /api/candidates` | `reports/data/candidates_all.parquet` |
| `GET /api/predictions?model=a1&delta=6&seed=42` | `reports/data/preds_*.json` merged with candidates |
| `GET /api/predictions/comparison` | `reports/tables/final_results.csv` |
| `GET /api/graph` | Graph built from candidates + flows + predictions |
| `GET /api/entity/{host_id}` | Host profile from candidates + flows |
| `GET /api/entities?search=C10` | Host search |
| `GET /api/redteam` | `reports/data/redteam_per_day.csv` |
| `GET /api/training_results` | `reports/tables/training_results.json` |
| `GET /api/model_metrics` | `reports/tables/final_results.csv` |
| `GET /api/slice_window` | `reports/slice_window.json` |
| `GET /api/throughput` | `reports/throughput.json` |
| `GET /api/coverage_ceiling` | `reports/coverage_ceiling.json` |
| `GET /health` | Health check |

## Demo Mode vs Live Backend

| Feature | Demo Mode (VITE_DEMO_MODE=true) | Live Backend |
|---------|------|------|
| System Status | All services shown as "offline" | Reflects actual Kafka/Spark/Neo4j status |
| Flow Events | 15 synthetic LANL-style events, auto-refresh | Real flows from parquet |
| Attack Graph | 20 demo nodes with confirmed + predicted hosts | Graph from candidates + flows parquet |
| Predictions | 10 demo predictions with realistic probabilities | Real model outputs from preds_*.json |
| Anomalies | 8 demo anomalies with severity/type | Generated from candidate analysis |
| Model Metrics | Hardcoded from final_results.csv values | Live from CSV |
| Visualizations | Links to pre-rendered HTML (served from /public/visualizations/) | Same |

**Demo mode is clearly indicated** with an amber banner: "⚠ DEMO MODE — Infrastructure offline."

## Data Integrity

- ✅ All SIMULATED_PROPAGATION edges clearly marked "not an observed network event"
- ✅ Predictions never presented as confirmed compromises
- ✅ Model AP=NaN honestly reported with explanation
- ✅ Coverage ceiling 0% shown with interpretation
- ✅ No fabricated algorithm outputs
- ✅ Existing Python backend untouched

## Startup Commands

```bash
# Terminal 1: Start backend adapter (optional — frontend works in demo mode without it)
cd e:\GitHub\dhap-net
pip install fastapi uvicorn pandas numpy
python -m uvicorn backend.main:app --port 8000

# Terminal 2: Start frontend
cd e:\GitHub\dhap-net\frontend
npm run dev

# Open: http://localhost:5173
```

## Project Structure

```
e:\GitHub\dhap-net\
├── backend/                    # NEW — FastAPI adapter (read-only, no algorithm changes)
│   ├── __init__.py
│   ├── main.py                 # All API endpoints
│   ├── requirements.txt
│   └── start.bat
├── frontend/                   # NEW — React frontend
│   ├── src/
│   │   ├── api/               # API client + service functions
│   │   ├── components/
│   │   │   ├── layout/        # Sidebar, TopBar, Layout
│   │   │   └── ui/            # MetricCard, StatusBadge, DataTable, etc.
│   │   ├── data/              # Demo fixtures (fixtures.ts)
│   │   ├── lib/               # Utilities (utils.ts)
│   │   ├── pages/             # 8 page components
│   │   ├── types/             # TypeScript interfaces (index.ts)
│   │   ├── App.tsx            # Router setup
│   │   └── index.css          # Dark cyber theme
│   ├── public/
│   │   └── visualizations/    # Copied from visualizations/ (15 HTML + PNG)
│   ├── .env                   # Demo mode config
│   ├── .env.production        # Production config
│   └── vite.config.ts         # Vite + Tailwind + proxy to backend
├── configs/                   # UNCHANGED
├── pipeline/                  # UNCHANGED
├── models/                    # UNCHANGED
├── reports/                   # UNCHANGED (read-only by backend adapter)
├── data/                      # UNCHANGED (read-only by backend adapter)
├── visualizations/            # UNCHANGED (copied to frontend/public/)
└── FRONTEND_SUMMARY.md        # This file
```

## Known Limitations

1. **Plotly charts** use CSS-based bar charts instead of Plotly.js to reduce bundle size — use the Visualizations Gallery for full Plotly interactivity
2. **Neo4j live queries** require Neo4j running (`docker compose up -d neo4j`) — Cypher queries shown in UI for manual use
3. **Parquet reading** may fail if pyarrow DLL is blocked — backend falls back to synthetic data with clear labeling
4. **No authentication** — add if deploying beyond localhost
5. **Attack graph** in demo mode uses 20 fixed nodes — connect backend for full candidate graph (150+ nodes)

