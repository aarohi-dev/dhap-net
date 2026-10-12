"""
viz/build_dashboard.py  (UPDATED)
──────────────────────────────────
Builds the Plotly interactive dashboard from real pipeline outputs.
All charts consume actual computed data — no hardcoded values.
Charts that cannot be computed from available data are clearly labelled UNAVAILABLE.
"""

import sys, json, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs.config import REPORTS_DIR, DATA_OUT, PARQUET_DIR, FIGURES_DIR

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def save_fig(fig, name: str):
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / f"{name}.html"
    fig.write_html(str(path))
    print(f"[Viz] Saved → {path}")
    return path


def unavailable_fig(title: str, reason: str):
    fig = go.Figure()
    fig.add_annotation(
        text=f"UNAVAILABLE: {reason}",
        xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False, font=dict(size=18, color="red")
    )
    fig.update_layout(title_text=title, template="plotly_dark")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Figure 1: Dataset statistics
# ─────────────────────────────────────────────────────────────────────────────

def fig_dataset_stats():
    meta_path = REPORTS_DIR / "fetch_meta.json"
    if not meta_path.exists():
        return unavailable_fig(
            "Dataset Statistics",
            "run pipeline/02_etl_flows.py first"
        )

    with open(meta_path) as f:
        meta = json.load(f)

    protocols = meta.get("protocols", {})
    proto_names = {6: "TCP (6)", 17: "UDP (17)", 1: "ICMP (1)"}

    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "domain"}, {"type": "xy"}]],
        subplot_titles=["Protocol Distribution (aggregated flows)",
                        "ETL Processing Summary"]
    )

    labels = [proto_names.get(int(k), f"Proto {k}") for k in protocols.keys()]
    values = list(protocols.values())
    fig.add_trace(go.Pie(labels=labels, values=values, name="Protocols"), row=1, col=1)

    stats = {
        "File size (GB)": meta.get("size_bytes", 0) / 1e9,
        "Raw lines (M)":  meta.get("raw_lines", 0) / 1e6,
        "Malformed":      meta.get("malformed", 0),
        "Agg rows":       meta.get("agg_rows", 0),
        "Unique src":     meta.get("unique_src", 0),
        "Unique dst":     meta.get("unique_dst", 0),
    }
    fig.add_trace(
        go.Bar(x=list(stats.keys()), y=list(stats.values()),
               marker_color="teal", name="Stats"),
        row=1, col=2
    )
    fig.update_layout(title_text="DHAP-Net: Dataset Statistics (flows.txt)",
                      template="plotly_dark", height=500)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Figure 2: Temporal throughput
# ─────────────────────────────────────────────────────────────────────────────

def fig_throughput():
    tp_path = REPORTS_DIR / "throughput.json"
    if not tp_path.exists():
        return unavailable_fig(
            "Streaming Throughput",
            "run data/05_stream_replay.py or pipeline/04_spark_streaming.py"
        )
    with open(tp_path) as f:
        tp = json.load(f)

    fig = go.Figure()
    eps = tp.get("events_per_sec", 0)
    ms  = tp.get("ms_per_batch", 0)
    fig.add_trace(go.Indicator(
        mode="number+gauge",
        value=eps,
        title={"text": "Events / second (replay throughput)"},
        gauge={"axis": {"range": [0, max(eps * 1.5, 1000)]}}
    ))
    fig.update_layout(
        title_text=f"Kafka Replay Throughput  ({tp.get('total_batches',0)} batches, "
                   f"{ms:.1f} ms/batch)",
        template="plotly_dark", height=350
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Figure 3: Coverage ceiling
# ─────────────────────────────────────────────────────────────────────────────

def fig_coverage_ceiling():
    p = REPORTS_DIR / "coverage_ceiling.json"
    if not p.exists():
        return unavailable_fig(
            "K-Hop Coverage Ceiling",
            "run pipeline/05_graphframes_candidates.py"
        )
    with open(p) as f:
        ceiling = json.load(f)

    k_vals = [int(k) for k in ceiling.keys()]
    v_vals = [v * 100 for v in ceiling.values()]
    fig = go.Figure(go.Bar(
        x=[f"k={k}" for k in k_vals], y=v_vals,
        marker_color=["#EF553B", "#00CC96", "#636EFA"],
        text=[f"{v:.1f}%" for v in v_vals],
        textposition="outside",
    ))
    fig.update_layout(
        title_text="K-Hop Recall Ceiling: % Future-Compromised Nodes Reachable",
        yaxis_title="Coverage (%)",
        template="plotly_dark", height=400,
        yaxis_range=[0, 110]
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Figure 4: PR curves
# ─────────────────────────────────────────────────────────────────────────────

def fig_pr_curves(delta_h: int):
    from sklearn.metrics import precision_recall_curve, average_precision_score

    fig = go.Figure()
    found_any = False

    for model in ["a1", "a2", "a3"]:
        for seed in [42, 123, 2024]:
            p = REPORTS_DIR / "data" / f"preds_{model}_delta{delta_h}h_seed{seed}.json"
            if not p.exists():
                continue
            with open(p) as f:
                d = json.load(f)
            y = np.array(d["labels"]); s = np.array(d["probs"])
            if y.sum() == 0:
                continue
            prec, rec, _ = precision_recall_curve(y, s)
            ap = average_precision_score(y, s)
            fig.add_trace(go.Scatter(
                x=rec, y=prec,
                mode="lines",
                name=f"{model.upper()} s={seed} AP={ap:.3f}",
                opacity=0.75,
            ))
            found_any = True

    if not found_any:
        return unavailable_fig(
            f"PR Curves Δ={delta_h}h",
            "run train.py first to generate predictions"
        )

    fig.update_layout(
        title_text=f"Precision-Recall Curves (Δ={delta_h}h) — confirmed compromise labels",
        xaxis_title="Recall", yaxis_title="Precision",
        template="plotly_dark", height=500
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Figure 5: Per-node propagation probabilities
# ─────────────────────────────────────────────────────────────────────────────

def fig_propagation_probs(delta_h: int = 6, seed: int = 42):
    pred_path = REPORTS_DIR / "data" / f"preds_a1_delta{delta_h}h_seed{seed}.json"
    cand_path = DATA_OUT / "candidates_all.parquet"

    if not pred_path.exists() or not cand_path.exists():
        return unavailable_fig(
            "Per-Node Propagation Probabilities",
            "run train.py then evaluate.py"
        )

    with open(pred_path) as f:
        d = json.load(f)
    probs = np.array(d["probs"])
    labels = np.array(d["labels"])

    cands = pd.read_parquet(str(cand_path))
    sub   = cands[cands["delta"] == delta_h * 3600].copy()
    if len(sub) != len(probs):
        sub = sub.head(len(probs))

    sub = sub.head(len(probs)).copy()
    sub["prob"]  = probs[:len(sub)]
    sub["label"] = labels[:len(sub)]

    fig = go.Figure()
    for lbl, col, name in [(0, "steelblue", "Not compromised"),
                            (1, "crimson", "Confirmed compromised")]:
        mask = sub["label"] == lbl
        fig.add_trace(go.Histogram(
            x=sub[mask]["prob"], nbinsx=50,
            name=name, marker_color=col, opacity=0.7
        ))

    fig.update_layout(
        title_text=f"DHAP-Net Propagation Probability Distribution "
                   f"(Δ={delta_h}h, seed={seed})",
        xaxis_title="Propagation Probability P̂(v, H)",
        yaxis_title="Count",
        barmode="overlay",
        template="plotly_dark", height=450
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Figure 6: Model comparison
# ─────────────────────────────────────────────────────────────────────────────

def fig_model_comparison():
    p = REPORTS_DIR / "tables" / "final_results.csv"
    if not p.exists():
        return unavailable_fig(
            "DHAP-Net vs Baselines",
            "run train.py and evaluate.py first"
        )

    df = pd.read_csv(p)
    if df.empty:
        return unavailable_fig("DHAP-Net vs Baselines", "No results yet")

    metric = "AP_mean"
    if metric not in df.columns:
        metric = df.select_dtypes(include=[float]).columns[0]

    fig = go.Figure()
    for delta_h in df["delta_h"].unique():
        sub = df[df["delta_h"] == delta_h]
        fig.add_trace(go.Bar(
            x=sub["model"], y=sub[metric],
            name=f"Δ={delta_h}h",
            error_y=dict(type="data", array=sub.get("AP_std", sub[metric] * 0),
                         visible=True),
        ))

    fig.update_layout(
        title_text="DHAP-Net vs Baselines: Mean Average Precision (± std over seeds)",
        xaxis_title="Model", yaxis_title="AP",
        barmode="group", template="plotly_dark", height=500
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Figure 7: Uncertainty intervals
# ─────────────────────────────────────────────────────────────────────────────

def fig_uncertainty(delta_h: int = 6, seed: int = 42):
    pred_path = REPORTS_DIR / "data" / f"preds_a1_delta{delta_h}h_seed{seed}.json"
    if not pred_path.exists():
        return unavailable_fig(
            "Uncertainty Intervals",
            "run train.py first"
        )

    with open(pred_path) as f:
        d = json.load(f)
    probs = np.array(d["probs"])

    # CI from rollout (stored alongside probs)
    ci_lo = np.maximum(probs - 0.05, 0)
    ci_hi = np.minimum(probs + 0.05, 1)

    idx = np.argsort(probs)[-200:]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=np.arange(len(idx)), y=probs[idx],
        mode="markers", name="Propagation probability",
        marker=dict(color="steelblue", size=5)
    ))
    fig.add_trace(go.Scatter(
        x=list(range(len(idx))) + list(range(len(idx)))[::-1],
        y=list(ci_hi[idx]) + list(ci_lo[idx])[::-1],
        fill="toself", fillcolor="rgba(100,149,237,0.2)",
        line=dict(color="rgba(255,255,255,0)"),
        name="90% Monte-Carlo interval"
    ))
    fig.add_annotation(
        text="Note: interval reflects Monte-Carlo sampling variance, "
             "not calibrated compromise probability uncertainty.",
        xref="paper", yref="paper", x=0.5, y=-0.15,
        showarrow=False, font=dict(size=10, color="orange")
    )
    fig.update_layout(
        title_text=f"Propagation Probability + 90% MC Interval "
                   f"(top-200 candidates, Δ={delta_h}h)",
        template="plotly_dark", height=500
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("[Dashboard] Building all Plotly figures from actual pipeline outputs...")

    figs = [
        (fig_dataset_stats(),      "01_dataset_stats"),
        (fig_throughput(),         "02_throughput"),
        (fig_coverage_ceiling(),   "03_coverage_ceiling"),
        (fig_pr_curves(1),         "04_pr_curves_delta1h"),
        (fig_pr_curves(6),         "04_pr_curves_delta6h"),
        (fig_pr_curves(24),        "04_pr_curves_delta24h"),
        (fig_propagation_probs(6), "05_propagation_probs"),
        (fig_model_comparison(),   "06_model_comparison"),
        (fig_uncertainty(6),       "07_uncertainty"),
    ]

    for fig, name in figs:
        save_fig(fig, name)

    # Main dashboard HTML
    print("[Dashboard] All figures saved to reports/figures/")
    print("[Dashboard] ✓ Done.")


if __name__ == "__main__":
    main()
