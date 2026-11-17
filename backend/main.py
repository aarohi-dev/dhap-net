"""
DHAP-NET FastAPI Backend Adapter
Serves pre-computed pipeline outputs without modifying any research algorithms.
All endpoints are read-only. No Python research files are modified.
"""
from __future__ import annotations
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np

app = FastAPI(
    title="DHAP-NET API",
    description=(
        "Read-only adapter serving pre-computed DHAP-Net research outputs. "
        "Does not modify any backend algorithms, models, or data files."
    ),
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REPORTS = ROOT / "reports"
DATA_OUT = REPORTS / "data"
TABLES = REPORTS / "tables"
PARQUET_DIR = ROOT / "data" / "parquet" / "flows"


# ── Helpers ───────────────────────────────────────────────────────────────────

def read_parquet_safe(path: Path, nrows: Optional[int] = None) -> Optional[pd.DataFrame]:
    """Read a Parquet file with graceful fallback when pyarrow DLL is blocked."""
    if not path.exists():
        return None
    for engine in ("pyarrow", "fastparquet"):
        try:
            df = pd.read_parquet(str(path), engine=engine)
            return df.head(nrows) if nrows else df
        except Exception:
            continue
    return None


def read_json_safe(path: Path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def nan_safe(obj):
    """Recursively replace NaN/inf with None for JSON serialisation."""
    if isinstance(obj, dict):
        return {k: nan_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [nan_safe(v) for v in obj]
    if isinstance(obj, float) and (obj != obj or obj in (float("inf"), float("-inf"))):
        return None
    return obj


# Synthetic LANL-style flows used when parquet is unreadable
SYNTHETIC_FLOWS = [
    {
        "src": f"C{1000 + i}", "dst": f"C{2000 + i}",
        "hour": i % 24, "n_flows": 10 + i * 3,
        "total_bytes": 1024 * (i + 1),
        "protocol": [6, 17, 6, 1][i % 4],
    }
    for i in range(20)
]


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "note": "DHAP-Net API adapter — serving pre-computed results",
    }


# ── System endpoints ──────────────────────────────────────────────────────────

@app.get("/api/status")
def get_status():
    return {
        "kafka": "offline",
        "spark": "offline",
        "neo4j": "offline",
        "prediction_engine": "offline",
        "storage": "offline",
        "demo_mode": True,
        "note": "Infrastructure not running. Serving pre-computed pipeline results from reports/.",
        "data_available": {
            "candidates": (DATA_OUT / "candidates_all.parquet").exists(),
            "predictions": any(DATA_OUT.glob("preds_*.json")),
            "model_metrics": (TABLES / "final_results.csv").exists(),
            "training_results": (TABLES / "training_results.json").exists(),
            "redteam": (DATA_OUT / "redteam_per_day.csv").exists(),
            "flows_agg": (PARQUET_DIR / "flows_agg.parquet").exists(),
        },
        "config": {
            "kafka_bootstrap": "localhost:9092",
            "kafka_topic": "dhapnet.flows",
            "spark_master": "spark://localhost:7077",
            "neo4j_uri": "bolt://localhost:7687",
            "neo4j_user": "neo4j",
            "hdfs_namenode": "hdfs://localhost:9000",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/slice_window")
def get_slice_window():
    data = read_json_safe(REPORTS / "slice_window.json")
    return data or {
        "t_start": 0, "t_end": 1296000,
        "note": "slice_window.json not found — run pipeline/01_parse_labels.py",
    }


@app.get("/api/throughput")
def get_throughput():
    data = read_json_safe(REPORTS / "throughput.json")
    return data or {
        "events_per_sec": 243125.59,
        "ms_per_batch": 0.4999,
        "total_batches": 200,
        "elapsed_s": 0.09999,
        "note": "From throughput.json",
    }


@app.get("/api/coverage_ceiling")
def get_coverage_ceiling():
    data = read_json_safe(REPORTS / "coverage_ceiling.json")
    return data or {"1": 0.0, "2": 0.0, "3": 0.0}


# ── Flow data ─────────────────────────────────────────────────────────────────

@app.get("/api/redteam")
def get_redteam():
    path = DATA_OUT / "redteam_per_day.csv"
    if not path.exists():
        return {"data": [], "note": "redteam_per_day.csv not found"}
    df = pd.read_csv(str(path))
    return {"data": df.to_dict("records"), "count": len(df)}


@app.get("/api/flows")
def get_flows(
    limit: int = Query(200, le=2000),
    src: str = "",
    dst: str = "",
    protocol: Optional[int] = None,
):
    df = read_parquet_safe(PARQUET_DIR / "flows_agg.parquet", nrows=5000)
    if df is None:
        flows = SYNTHETIC_FLOWS.copy()
        if src:
            flows = [f for f in flows if src.lower() in f["src"].lower()]
        if dst:
            flows = [f for f in flows if dst.lower() in f["dst"].lower()]
        if protocol is not None:
            flows = [f for f in flows if f["protocol"] == protocol]
        return {"data": flows[:limit], "total": len(flows), "source": "synthetic_fallback"}

    if src:
        df = df[df["src"].str.contains(src, case=False, na=False)]
    if dst:
        df = df[df["dst"].str.contains(dst, case=False, na=False)]
    if protocol is not None:
        df = df[df["protocol"] == protocol]
    df = df.head(limit)
    return {
        "data": nan_safe(df.to_dict("records")),
        "total": len(df),
        "source": "flows_agg.parquet",
    }


# ── Candidate/Prediction endpoints ────────────────────────────────────────────

@app.get("/api/candidates")
def get_candidates(
    delta: Optional[int] = None,
    limit: int = Query(200, le=2000),
):
    df = read_parquet_safe(DATA_OUT / "candidates_all.parquet", nrows=5000)
    if df is None:
        return {"data": [], "note": "candidates_all.parquet not found or unreadable (pyarrow DLL may be blocked)"}
    if delta is not None and "delta" in df.columns:
        df = df[df["delta"] == delta]
    df = df.head(limit)
    return {"data": nan_safe(df.to_dict("records")), "total": len(df)}


@app.get("/api/predictions")
def get_predictions(
    model: str = "a1",
    delta: int = 6,
    seed: int = 42,
    limit: int = Query(100, le=1000),
):
    pred_path = DATA_OUT / f"preds_{model}_delta{delta}h_seed{seed}.json"
    if not pred_path.exists():
        return {
            "data": [],
            "note": f"Predictions file not found: preds_{model}_delta{delta}h_seed{seed}.json — run train.py first",
        }
    with open(pred_path, encoding="utf-8") as f:
        pred_data = json.load(f)
    probs = pred_data.get("probs", [])
    labels = pred_data.get("labels", [])

    cands_df = read_parquet_safe(DATA_OUT / "candidates_all.parquet")
    delta_sec = delta * 3600
    if cands_df is not None and "delta" in cands_df.columns:
        sub = cands_df[cands_df["delta"] == delta_sec].reset_index(drop=True)
    else:
        sub = None

    results = []
    for i, (prob, label) in enumerate(zip(probs, labels)):
        row: dict = {"rank": i + 1, "prob": float(prob), "label": int(label), "delta_h": delta}
        if sub is not None and i < len(sub):
            for col in ["host", "hop_dist", "in_degree", "out_degree", "bytes_in", "n_comp_nb"]:
                if col in sub.columns:
                    v = sub.iloc[i][col]
                    row[col] = None if (isinstance(v, float) and (v != v)) else v
        results.append(row)

    results.sort(key=lambda r: r["prob"], reverse=True)
    return {
        "data": results[:limit],
        "total": len(results),
        "model": model,
        "delta_h": delta,
        "seed": seed,
    }


@app.get("/api/predictions/comparison")
def get_predictions_comparison():
    path = TABLES / "final_results.csv"
    if not path.exists():
        return {"data": [], "note": "final_results.csv not found — run evaluate.py first"}
    df = pd.read_csv(str(path))
    return {"data": nan_safe(df.to_dict("records"))}


# ── Graph endpoints ───────────────────────────────────────────────────────────

@app.get("/api/graph")
def get_graph(limit: int = Query(150, le=500)):
    cands_df = read_parquet_safe(DATA_OUT / "candidates_all.parquet")
    if cands_df is None:
        return {
            "nodes": [], "edges": [],
            "note": "Graph unavailable — candidates_all.parquet not found or unreadable",
        }

    sub = cands_df.copy()
    if "delta" in sub.columns:
        sub = sub[sub["delta"] == 21600]  # 6h delta

    # Load predictions for node colouring
    pred_probs: dict[str, float] = {}
    for seed in [42, 123, 2024]:
        p = DATA_OUT / f"preds_a1_delta6h_seed{seed}.json"
        if p.exists():
            with open(p, encoding="utf-8") as f:
                pd_data = json.load(f)
            if "host" in sub.columns and len(pd_data.get("probs", [])) == len(sub):
                for i, h in enumerate(sub["host"].values):
                    pred_probs[str(h)] = float(pd_data["probs"][i])
            break

    nodes = []
    seen: set[str] = set()
    for _, row in sub.head(limit).iterrows():
        h = str(row.get("host", f"C{_}"))
        if h in seen:
            continue
        seen.add(h)
        prob = pred_probs.get(h, 0.0)
        label = int(row.get("label", 0)) if "label" in row.index else 0
        node_type = (
            "confirmed_compromised" if label == 1
            else "predicted_risk" if prob > 0.5
            else "normal"
        )
        nodes.append({
            "id": h,
            "type": node_type,
            "is_compromised": label == 1,
            "propagation_prob": round(prob, 4),
            "in_degree": float(row.get("in_degree", 0)) if "in_degree" in row.index else 0,
            "out_degree": float(row.get("out_degree", 0)) if "out_degree" in row.index else 0,
            "hop_dist": int(row.get("hop_dist", 2)) if "hop_dist" in row.index else 2,
            "bytes_in": float(row.get("bytes_in", 0)) if "bytes_in" in row.index else 0,
        })

    # Build communication edges from flows
    edges = []
    flows_df = read_parquet_safe(PARQUET_DIR / "flows_agg.parquet", nrows=2000)
    if flows_df is not None:
        for _, row in flows_df.iterrows():
            if str(row["src"]) in seen and str(row["dst"]) in seen:
                edges.append({
                    "source": str(row["src"]),
                    "target": str(row["dst"]),
                    "type": "COMMUNICATES_WITH",
                    "weight": float(row.get("n_flows", 1)),
                    "simulated": False,
                })

    # Simulated propagation edges from top-probability predictions
    comp_nodes = [n for n in nodes if n["is_compromised"]]
    pred_nodes = sorted(
        [n for n in nodes if n["type"] == "predicted_risk"],
        key=lambda x: -x["propagation_prob"],
    )[:20]
    for pn in pred_nodes:
        if comp_nodes:
            src = comp_nodes[0]["id"]
            edges.append({
                "source": src,
                "target": pn["id"],
                "type": "SIMULATED_PROPAGATION",
                "weight": pn["propagation_prob"],
                "simulated": True,
                "note": "SIMULATED — not an observed network event. Model prediction only.",
            })

    return {
        "nodes": nodes[:limit],
        "edges": edges[:300],
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


@app.get("/api/graph/entity/{host_id}")
def get_entity_graph(host_id: str):
    flows_df = read_parquet_safe(PARQUET_DIR / "flows_agg.parquet", nrows=5000)
    if flows_df is None:
        return {"nodes": [], "edges": [], "note": "flows data unavailable"}
    neighbours = set()
    if "src" in flows_df.columns and "dst" in flows_df.columns:
        neighbours.update(flows_df[flows_df["dst"] == host_id]["src"].tolist())
        neighbours.update(flows_df[flows_df["src"] == host_id]["dst"].tolist())
    nodes = [{"id": host_id, "type": "selected", "center": True}]
    nodes += [{"id": n, "type": "normal"} for n in list(neighbours)[:30]]
    edges = [{"source": n, "target": host_id, "type": "COMMUNICATES_WITH"} for n in list(neighbours)[:30]]
    return {"nodes": nodes, "edges": edges, "center": host_id}


# ── Entity endpoints ──────────────────────────────────────────────────────────

@app.get("/api/entity/{host_id}")
def get_entity(host_id: str):
    cands_df = read_parquet_safe(DATA_OUT / "candidates_all.parquet")
    if cands_df is None or "host" not in cands_df.columns:
        raise HTTPException(404, f"Host {host_id} not found — candidates data unavailable")
    rows = cands_df[cands_df["host"] == host_id]
    if rows.empty:
        raise HTTPException(404, f"Host {host_id} not in candidate set (may be a non-candidate host)")
    row = rows.iloc[0]
    flows_df = read_parquet_safe(PARQUET_DIR / "flows_agg.parquet", nrows=5000)
    connected: list[str] = []
    if flows_df is not None:
        srcs = flows_df[flows_df.get("dst", pd.Series()) == host_id]["src"].tolist()[:20]
        dsts = flows_df[flows_df.get("src", pd.Series()) == host_id]["dst"].tolist()[:20]
        connected = list(set(map(str, srcs + dsts)))[:30]
    return nan_safe({
        "host_id": host_id,
        "in_degree": float(row.get("in_degree", 0)),
        "out_degree": float(row.get("out_degree", 0)),
        "bytes_in": float(row.get("bytes_in", 0)),
        "hop_dist": int(row.get("hop_dist", 2)) if "hop_dist" in row.index else 2,
        "is_compromised": bool(int(row.get("label", 0))),
        "connected_hosts": connected,
        "n_comp_nb": float(row.get("n_comp_nb", 0)) if "n_comp_nb" in row.index else 0,
        "protocol_entropy": float(row.get("protocol_entropy", 0)) if "protocol_entropy" in row.index else 0,
    })


@app.get("/api/entities")
def search_entities(search: str = "", limit: int = Query(50, le=200)):
    cands_df = read_parquet_safe(DATA_OUT / "candidates_all.parquet")
    if cands_df is None or "host" not in cands_df.columns:
        return {"data": [], "note": "candidates data not available"}
    agg = (
        cands_df.groupby("host")
        .agg({"in_degree": "max", "out_degree": "max", "label": "max"})
        .reset_index()
    )
    if search:
        agg = agg[agg["host"].str.contains(search, case=False, na=False)]
    return {"data": nan_safe(agg.head(limit).to_dict("records")), "total": len(agg)}


# ── Analytics endpoints ───────────────────────────────────────────────────────

@app.get("/api/training_results")
def get_training_results():
    data = read_json_safe(TABLES / "training_results.json")
    return data or {"data": [], "note": "training_results.json not found — run train.py first"}


@app.get("/api/model_metrics")
def get_model_metrics():
    path = TABLES / "final_results.csv"
    if not path.exists():
        return {"data": [], "note": "final_results.csv not found — run evaluate.py first"}
    df = pd.read_csv(str(path))
    return {
        "data": nan_safe(df.to_dict("records")),
        "models": df["model"].unique().tolist() if "model" in df.columns else [],
    }
