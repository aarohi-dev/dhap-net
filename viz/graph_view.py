"""
Graph view (Section 6.5 C):
  11. Interactive graph of compromised hosts + k-hop candidates
      (node colour = predicted risk, edge colour = edge type)
  12. Time slider showing risk evolution across micro-batches
  13. Top predicted propagation path for case-study events

Uses PyVis for the main graph (self-contained HTML, no server needed).
Uses Plotly for the time-slider animation.

Run: python viz/graph_view.py
"""

import sys, json, collections, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configs.config import (
    DATA_DIR, PARQUET_DIR, REPORTS_DIR, FIGURES_DIR,
    K_HOPS, WINDOW_S
)

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from pyvis.network import Network

# ── Risk color scale ──────────────────────────────────────────────────────────
def risk_to_color(risk: float) -> str:
    """Map 0-1 risk to white→red hex."""
    r = int(255)
    g = int(255 * (1 - risk))
    b = int(255 * (1 - risk))
    return f"#{r:02x}{g:02x}{b:02x}"

EDGE_COLORS = {
    "auth": "#3A86FF",
    "user_logon": "#8338EC",
    "comm": "#06D6A0",
    "flow": "#06D6A0",
    "6": "#3A86FF",       # TCP
    "17": "#FFB703",      # UDP
    "1": "#E63946",       # ICMP
    "dns_lookup": "#FFB703",
    "belongs_to": "#FB8500",
}

# ── Build neighbourhood graph ─────────────────────────────────────────────────
def build_neighbourhood(auth_df: pd.DataFrame,
                         compr_times: dict,
                         t: int,
                         risk_scores: dict,
                         k: int = K_HOPS,
                         max_nodes: int = 200) -> tuple[dict, list]:
    """
    Returns (nodes_dict, edges_list) for the k-hop neighbourhood at time t.
    nodes_dict: {host: {"risk": float, "compromised": bool, "type": str}}
    edges_list: [{"src": str, "dst": str, "rel": str}]
    """
    C_t = {h for h, tv in compr_times.items() if tv <= t}

    w_low = max(0, t - WINDOW_S)
    w_df  = auth_df[
        (auth_df["hour"] * 3600 >= w_low) &
        (auth_df["hour"] * 3600 < t)
    ]

    # Build adjacency
    adj = collections.defaultdict(set)
    for _, row in w_df.iterrows():
        s = row.get("src_host", row.get("src", None))
        d = row.get("dst_host", row.get("dst", None))
        if pd.notna(s) and pd.notna(d):
            adj[s].add(d)

    # BFS from C_t
    nodes_in_graph = set(C_t)
    frontier = set(C_t)
    for _ in range(k):
        nxt = set()
        for n in frontier:
            for m in adj.get(n, set()):
                if m not in nodes_in_graph:
                    nxt.add(m)
                    nodes_in_graph.add(m)
        frontier = nxt

    # Limit for readability
    if len(nodes_in_graph) > max_nodes:
        # Keep compromised + highest-risk candidates
        by_risk = sorted(nodes_in_graph - C_t,
                         key=lambda h: risk_scores.get(h, 0), reverse=True)
        nodes_in_graph = C_t | set(by_risk[:max_nodes - len(C_t)])

    nodes = {}
    for h in nodes_in_graph:
        nodes[h] = {
            "risk": risk_scores.get(h, 0.0),
            "compromised": h in C_t,
            "type": "Host",
        }

    edges = []
    for _, row in w_df.iterrows():
        src = row.get("src_host", row.get("src", ""))
        dst = row.get("dst_host", row.get("dst", ""))
        if src in nodes and dst in nodes and src != dst:
            proto = str(row.get("protocol", row.get("auth_type", "comm")))
            edges.append({"src": src, "dst": dst, "rel": f"flow_{proto}"})

    return nodes, edges

# ── PyVis graph ───────────────────────────────────────────────────────────────
def make_pyvis_graph(nodes: dict, edges: list,
                     title: str = "Attack propagation graph",
                     out_path: Path = None) -> str:
    net = Network(height="800px", width="100%", bgcolor="#1a1a2e",
                  font_color="white", directed=True)
    net.toggle_physics(True)
    net.set_options("""
    {
      "nodes": {"borderWidth": 2, "shadow": true},
      "edges": {"smooth": {"type": "dynamic"}, "arrows": {"to": {"enabled": true}}},
      "physics": {"forceAtlas2Based": {"gravitationalConstant": -50},
                  "maxVelocity": 50, "solver": "forceAtlas2Based",
                  "timestep": 0.35, "stabilization": {"iterations": 150}}
    }
    """)

    for host, info in nodes.items():
        risk   = info["risk"]
        color  = "#FF4444" if info["compromised"] else risk_to_color(risk)
        border = "#FFD60A" if info["compromised"] else "#FFFFFF"
        shape  = "star" if info["compromised"] else "dot"
        label  = host[:15]   # truncate long names
        title  = (f"<b>{host}</b><br>"
                  f"Risk: {risk:.3f}<br>"
                  f"{'⚠ COMPROMISED' if info['compromised'] else 'Candidate'}")
        net.add_node(host, label=label, title=title,
                     color={"background": color, "border": border},
                     shape=shape, size=20 if info["compromised"] else 12)

    seen_edges = set()
    for e in edges:
        key = (e["src"], e["dst"])
        if key in seen_edges:
            continue
        seen_edges.add(key)
        rel   = e["rel"]
        color = EDGE_COLORS.get(rel.split("_")[0], "#AAAAAA")
        net.add_edge(e["src"], e["dst"], color=color, title=rel, width=1.5)

    if out_path is None:
        out_path = FIGURES_DIR / "11_attack_graph.html"
    net.save_graph(str(out_path))
    print(f"[Graph] Saved: {out_path.name}")
    return str(out_path)

# ── Time-slider Plotly animation ──────────────────────────────────────────────
def make_time_slider(auth_df: pd.DataFrame, compr_times: dict,
                     risk_by_hour: dict, hours_to_show: list = None):
    """
    Creates a Plotly figure with a time slider stepping through
    micro-batches. Nodes are placed with a simple spring layout.
    """
    if hours_to_show is None:
        all_hours = sorted(auth_df["hour"].unique())
        hours_to_show = all_hours[::6][:24]   # every 6 hours, up to 24 steps

    # Collect all nodes across frames
    all_nodes = set(compr_times.keys())
    for h in hours_to_show:
        risk_by_hour.get(h, {}).keys()
        all_nodes.update(risk_by_hour.get(h, {}).keys())
    all_nodes = list(all_nodes)

    # Simple circular layout
    n = len(all_nodes)
    angles = np.linspace(0, 2*np.pi, n, endpoint=False)
    pos = {node: (np.cos(a), np.sin(a)) for node, a in zip(all_nodes, angles)}

    frames = []
    for h in hours_to_show:
        t    = h * 3600
        C_t  = {nd for nd, tv in compr_times.items() if tv <= t}
        risk = risk_by_hour.get(h, {})

        xs, ys, texts, colors, sizes = [], [], [], [], []
        for nd in all_nodes:
            x, y = pos[nd]
            xs.append(x); ys.append(y)
            r = risk.get(nd, 0.0)
            texts.append(f"{nd[:12]}<br>risk={r:.3f}")
            if nd in C_t:
                colors.append("red"); sizes.append(18)
            else:
                colors.append(f"rgb({int(255)},{int(255*(1-r))},{int(255*(1-r))})"); sizes.append(10)

        frame = go.Frame(
            data=[go.Scatter(
                x=xs, y=ys, mode="markers+text",
                marker=dict(color=colors, size=sizes,
                            line=dict(width=1, color="white")),
                text=[nd[:8] for nd in all_nodes],
                textposition="top center",
                textfont=dict(size=8),
                hovertext=texts, hoverinfo="text",
            )],
            name=str(h),
        )
        frames.append(frame)

    fig = go.Figure(
        data=frames[0].data if frames else [],
        frames=frames,
        layout=go.Layout(
            title="Risk evolution over micro-batches (time slider)",
            template="plotly_dark",
            height=700,
            updatemenus=[dict(
                type="buttons", showactive=False, y=1.05, x=0.5,
                xanchor="center",
                buttons=[dict(label="▶ Play",
                              method="animate",
                              args=[None, {"frame": {"duration": 800, "redraw": True},
                                          "fromcurrent": True}]),
                         dict(label="⏹ Pause",
                              method="animate",
                              args=[[None], {"frame": {"duration": 0},
                                            "mode": "immediate"}])]
            )],
            sliders=[dict(
                steps=[dict(method="animate",
                            args=[[str(h)], {"frame": {"duration": 300}, "mode": "immediate"}],
                            label=f"h={h}") for h in hours_to_show],
                active=0, y=-0.05, x=0.1, len=0.8,
                currentvalue=dict(prefix="Hour: ", visible=True, xanchor="center"),
            )],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            font=dict(family="Inter, sans-serif"),
        )
    )
    out = FIGURES_DIR / "12_time_slider.html"
    fig.write_html(str(out))
    print(f"[Graph] Saved: {out.name}")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    auth_path  = PARQUET_DIR / "auth" / "auth_agg.parquet"
    flows_path = PARQUET_DIR / "flows" / "flows_agg.parquet"
    rt_path    = DATA_DIR / "redteam_labels.csv"

    if auth_path.exists():
        auth_df = pd.read_parquet(str(auth_path))
    elif flows_path.exists():
        auth_df = pd.read_parquet(str(flows_path))
    else:
        auth_df = None

    if auth_df is None or not rt_path.exists():
        print("[Graph] Data not found. Run ETL and data scripts first.")
        print("[Graph] Generating placeholder graph …")
        # Placeholder graph for demonstration
        nodes = {
            "C1001": {"risk": 1.0, "compromised": True, "type": "Host"},
            "C1002": {"risk": 0.72, "compromised": False, "type": "Host"},
            "C1003": {"risk": 0.58, "compromised": False, "type": "Host"},
            "C1004": {"risk": 0.31, "compromised": False, "type": "Host"},
            "C1005": {"risk": 0.15, "compromised": False, "type": "Host"},
        }
        edges = [
            {"src": "C1001", "dst": "C1002", "rel": "auth_NTLM"},
            {"src": "C1001", "dst": "C1003", "rel": "auth_Kerberos"},
            {"src": "C1002", "dst": "C1004", "rel": "auth_NTLM"},
            {"src": "C1003", "dst": "C1005", "rel": "auth_Kerberos"},
        ]
        make_pyvis_graph(nodes, edges, "Placeholder attack propagation graph")
        return

    rt = pd.read_csv(rt_path)
    compr_times = rt.groupby("dst")["time"].min().to_dict()
    src_only = set(rt["src"].unique()) - set(rt["dst"].unique())
    for h in src_only:
        compr_times[h] = int(rt[rt["src"] == h]["time"].min())

    # Choose a representative time (middle of red-team window)
    t_mid = (rt["time"].min() + rt["time"].max()) // 2

    # Load risk scores if available (from A1 predictions)
    risk_scores: dict = {}
    preds_path = REPORTS_DIR / "data" / "preds_a1_delta6h_seed42.json"
    cands_path = REPORTS_DIR / "data" / "candidates_all.parquet"
    if preds_path.exists() and cands_path.exists():
        with open(preds_path) as f:
            d = json.load(f)
        cands = pd.read_parquet(str(cands_path))
        cands = cands[cands["delta"] == 6*3600].copy()
        probs = np.array(d["probs"])
        # Map to host names (approximate – last test batch)
        n = min(len(probs), len(cands))
        for i in range(n):
            risk_scores[str(cands.iloc[i]["host"])] = float(probs[i])

    nodes, edges = build_neighbourhood(auth_df, compr_times, t_mid, risk_scores)
    print(f"[Graph] t={t_mid}s: {len(nodes)} nodes, {len(edges)} edges")
    make_pyvis_graph(nodes, edges,
                     title=f"Attack propagation graph at t={t_mid//3600}h")

    # Time slider
    hours = sorted(auth_df["hour"].unique())
    h_start = rt["time"].min() // 3600
    h_end   = rt["time"].max() // 3600
    slider_hours = [h for h in hours if h_start <= h <= h_end][::3][:20]

    # Build risk_by_hour (placeholder until A1 predictions are available)
    risk_by_hour: dict = {h: {} for h in slider_hours}
    make_time_slider(auth_df, compr_times, risk_by_hour, slider_hours)
    print("[Graph] ✓ Graph view done.")

if __name__ == "__main__":
    main()
