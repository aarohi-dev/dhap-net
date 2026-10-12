"""
EDA figures (Section 6.5 A):
  1. Red-team events per day + auth volume timeline
  2. Auth events per hour by auth_type and logon_type
  3. Degree distribution (log-log) + compromised hosts over time

Run: python viz/eda_figs.py
"""

import sys, json, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configs.config import DATA_DIR, PARQUET_DIR, REPORTS_DIR, FIGURES_DIR

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── helpers ───────────────────────────────────────────────────────────────────
def save(fig, name: str):
    html_path = FIGURES_DIR / f"{name}.html"
    png_path  = FIGURES_DIR / f"{name}.png"
    fig.write_html(str(html_path))
    try:
        fig.write_image(str(png_path), width=1200, height=600, scale=2)
    except Exception:
        pass
    print(f"[EDA] Saved: {html_path.name}")

# ── Fig 1: Red-team events per day + auth volume timeline ─────────────────────
def fig_redteam_timeline():
    rt_path = DATA_DIR / "redteam_labels.csv"
    if not rt_path.exists():
        print("[EDA] redteam_labels.csv not found – skipping Fig 1")
        return

    rt = pd.read_csv(rt_path)
    rt["day"] = rt["time"] // 86400
    per_day = rt.groupby("day").size().reset_index(name="n_events")

    # Auth volume (hourly from parquet)
    auth_path = PARQUET_DIR / "auth" / "auth_agg.parquet"
    auth_day = None
    if auth_path.exists():
        auth = pd.read_parquet(str(auth_path))
        auth["day"] = auth["hour"] // 24
        auth_day = auth.groupby("day")["n_events"].sum().reset_index()

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=[
            "Auth events per day (background) with red-team window marked",
            "Red-team events per day"
        ],
        vertical_spacing=0.12,
    )

    if auth_day is not None:
        fig.add_trace(go.Bar(
            x=auth_day["day"], y=auth_day["n_events"],
            name="Auth events", marker_color="#3A86FF", opacity=0.7,
        ), row=1, col=1)

    # Mark red-team window
    if not per_day.empty:
        d_min = int(per_day["day"].min())
        d_max = int(per_day["day"].max())
        fig.add_vrect(x0=d_min, x1=d_max,
                      fillcolor="rgba(255,70,70,0.15)",
                      layer="below", line_width=0, row=1, col=1)

    fig.add_trace(go.Bar(
        x=per_day["day"], y=per_day["n_events"],
        name="Red-team events", marker_color="#FF006E",
    ), row=2, col=1)

    fig.update_layout(
        title_text="LANL 2015 – Auth volume and red-team events by day",
        height=700, template="plotly_dark",
        legend=dict(orientation="h", y=-0.12),
        font=dict(family="Inter, sans-serif"),
    )
    fig.update_xaxes(title_text="Day from capture start", row=2)
    fig.update_yaxes(title_text="Events", row=1)
    fig.update_yaxes(title_text="Red-team events", row=2)

    # Save backing data
    per_day.to_csv(REPORTS_DIR / "data" / "redteam_per_day.csv", index=False)
    save(fig, "01_redteam_timeline")

# -- Fig 2: Flow events per hour by protocol ---------------------------------
def fig_auth_types():
    flows_path = PARQUET_DIR / "flows" / "flows_agg.parquet"
    if not flows_path.exists():
        print("[EDA] flows_agg.parquet not found - skipping Fig 2")
        return

    flows = pd.read_parquet(str(flows_path))

    # By protocol
    by_proto = (flows.groupby(["hour","protocol"])["n_flows"]
                .sum().reset_index())
    top_p = (flows.groupby("protocol")["n_flows"].sum()
             .nlargest(5).index.tolist())
    by_proto = by_proto[by_proto["protocol"].isin(top_p)]

    fig = px.area(
        by_proto, x="hour", y="n_flows", color="protocol",
        title="Flow events per hour by protocol (top 5)",
        labels={"hour": "Hour from start", "n_flows": "Flows",
                "protocol": "Protocol"},
        template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig.update_layout(font=dict(family="Inter, sans-serif"), height=500)
    by_proto.to_csv(REPORTS_DIR / "data" / "flows_by_protocol.csv", index=False)
    save(fig, "02_auth_types")

    # By src/dst bytes heatmap (top-10 src)
    top_src = (flows.groupby("src")["total_bytes"].sum()
               .nlargest(10).index.tolist())
    by_src = (flows[flows["src"].isin(top_src)]
              .groupby(["hour","src"])["n_flows"].sum().reset_index())
    fig2 = px.area(
        by_src, x="hour", y="n_flows", color="src",
        title="Flow events per hour (top 10 source hosts)",
        labels={"hour": "Hour", "n_flows": "Flows", "src": "Source host"},
        template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Vivid,
    )
    fig2.update_layout(font=dict(family="Inter, sans-serif"), height=500)
    save(fig2, "02b_logon_types")

# -- Fig 3: Degree distribution + compromised hosts over time ----------------
def fig_degree_dist():
    flows_path = PARQUET_DIR / "flows" / "flows_agg.parquet"
    if not flows_path.exists():
        print("[EDA] flows_agg.parquet not found - skipping Fig 3")
        return

    flows = pd.read_parquet(str(flows_path))
    deg = (flows.groupby("src")["n_flows"].sum()
           .sort_values(ascending=False))

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=[
            "Host degree distribution (log-log scale)",
            "Cumulative compromised hosts over time"
        ]
    )

    # Log-log degree
    counts = np.sort(deg.values)[::-1]
    rank   = np.arange(1, len(counts)+1)
    fig.add_trace(go.Scatter(
        x=np.log10(rank), y=np.log10(counts + 1),
        mode="lines", name="Out-degree",
        line=dict(color="#3A86FF", width=2)
    ), row=1, col=1)

    # Compromised hosts over time
    rt_path = DATA_DIR / "redteam_labels.csv"
    if rt_path.exists():
        rt = pd.read_csv(rt_path)
        comp_times = rt.groupby("dst")["time"].min().sort_values()
        cumulative = np.arange(1, len(comp_times)+1)
        fig.add_trace(go.Scatter(
            x=comp_times.values / 3600, y=cumulative,
            mode="lines+markers", name="Cumulative compromised hosts",
            line=dict(color="#FF006E", width=2),
            marker=dict(size=5)
        ), row=1, col=2)

    fig.update_xaxes(title_text="log₁₀(rank)", row=1, col=1)
    fig.update_yaxes(title_text="log₁₀(degree+1)", row=1, col=1)
    fig.update_xaxes(title_text="Hours from capture start", row=1, col=2)
    fig.update_yaxes(title_text="Cumulative hosts", row=1, col=2)
    fig.update_layout(
        title_text="Host graph structure and compromise progression",
        template="plotly_dark", height=500,
        font=dict(family="Inter, sans-serif"),
    )

    deg_df = pd.DataFrame({"rank": rank, "degree": counts})
    deg_df.to_csv(REPORTS_DIR / "data" / "degree_dist.csv", index=False)
    save(fig, "03_degree_dist")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("[EDA] Generating data-understanding figures …")
    fig_redteam_timeline()
    fig_auth_types()
    fig_degree_dist()
    print("[EDA] ✓ All EDA figures done.")

if __name__ == "__main__":
    main()
