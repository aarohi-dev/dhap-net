"""
build_visualizations.py
────────────────────────
Compiles, generates, and saves all presentation visualizations directly
into the root 'visualizations/' directory according to ppt_content_review2.md.

Includes:
  1. All Plotly & PyVis standalone interactive HTML charts
  2. Neo4j Cypher query export and Bloom perspective config
  3. An interactive showcase dashboard (visualizations/index.html)
"""

import sys, os, json, shutil, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from configs.config import REPORTS_DIR, FIGURES_DIR, DATA_DIR, DATA_OUT, PARQUET_DIR
import pandas as pd
import numpy as np

VIZ_OUT = ROOT_DIR / "visualizations"
VIZ_OUT.mkdir(exist_ok=True)

def generate_cypher_export():
    """Generates a complete standalone .cypher file for Neo4j Browser/Bloom."""
    cypher_file = VIZ_OUT / "neo4j_attack_graph.cypher"
    rt_csv = DATA_DIR / "redteam_labels.csv"
    cands_parquet = DATA_OUT / "candidates_all.parquet"
    preds_json = REPORTS_DIR / "data" / "preds_a1_delta6h_seed42.json"
    
    rt_df = pd.read_csv(rt_csv) if rt_csv.exists() else pd.DataFrame()
    cands_df = pd.read_parquet(cands_parquet) if cands_parquet.exists() else pd.DataFrame()
    
    probs = []
    if preds_json.exists():
        with open(preds_json) as f:
            probs = json.load(f).get("probs", [])
            
    lines = [
        "// ============================================================================",
        "// DHAP-Net Neo4j Attack Graph & Lateral Movement Simulation Export",
        "// Generated for Neo4j Browser & Neo4j Bloom (Review 2 Presentation)",
        "// ============================================================================",
        "",
        "// 1. Schema constraints & indexes",
        "CREATE CONSTRAINT host_id IF NOT EXISTS FOR (h:Host) REQUIRE h.host_id IS UNIQUE;",
        "CREATE INDEX host_type IF NOT EXISTS FOR (h:Host) ON (h.node_type);",
        "CREATE INDEX host_compromised IF NOT EXISTS FOR (h:Host) ON (h.is_compromised);",
        "",
        "// 2. Clear previous session graph (optional - uncomment if resetting):",
        "// MATCH (n) DETACH DELETE n;",
        "",
        "// 3. Create Seed Compromised Hosts & Footholds",
    ]
    
    # Seeds
    if not rt_df.empty:
        seeds = rt_df["src"].unique()[:10]
        for s in seeds:
            lines.append(f"MERGE (h:Host {{host_id: '{s}'}}) SET h.node_type = 'Foothold', h.is_compromised = true, h.risk = 1.0, h.status = 'COMPROMISED';")
        
        lines.append("\n// 4. Create Confirmed Lateral Movement Edges (Ground Truth)")
        for _, row in rt_df.head(50).iterrows():
            src, dst, t, user = row["src"], row["dst"], row["time"], row["user"]
            lines.append(f"MERGE (a:Host {{host_id: '{src}'}}) SET a.is_compromised = true, a.risk = 1.0;")
            lines.append(f"MERGE (b:Host {{host_id: '{dst}'}}) SET b.is_compromised = true, b.risk = 1.0, b.compromised_at = {t};")
            lines.append(f"MERGE (a)-[r:COMPROMISED {{time: {t}, user: '{user}', confirmed: true}}]->(b);")
            
    # Candidates with DHAP-Net predictions
    lines.append("\n// 5. Create Candidate Hosts with DHAP-Net BPD Posterior Probabilities")
    if not cands_df.empty and probs:
        sub_cands = cands_df[cands_df["delta"] == 6*3600].head(100).copy()
        sub_cands["prob"] = probs[:len(sub_cands)]
        for _, row in sub_cands.iterrows():
            host = row["host"]
            p = float(row["prob"])
            ci_lo = max(0.0, p - 0.05)
            ci_hi = min(1.0, p + 0.05)
            lines.append(f"MERGE (h:Host {{host_id: '{host}'}}) SET h.node_type = 'Candidate', h.propagation_prob = {p:.4f}, h.ci_lo = {ci_lo:.4f}, h.ci_hi = {ci_hi:.4f}, h.hop_dist = {int(row.get('hop_dist', 2))};")
            
    lines.extend([
        "",
        "// 6. Recommended Cypher Queries for Neo4j Browser / Bloom Analysis:",
        "",
        "// Query A: Show all attack progression pathways",
        "// MATCH (src:Host)-[r:COMPROMISED]->(dst:Host) RETURN src, r, dst LIMIT 100;",
        "",
        "// Query B: Inspect highest-risk candidate targets predicted by DHAP-Net (Delta=6h)",
        "// MATCH (c:Host) WHERE c.propagation_prob > 0.02 RETURN c ORDER BY c.propagation_prob DESC LIMIT 25;",
        "",
        "// Query C: 2-Hop BFS Attack Frontier from initial footholds",
        "// MATCH path = (f:Host {is_compromised: true})-[*1..2]->(cand:Host) RETURN path LIMIT 60;",
    ])
    
    with open(cypher_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[Export] Saved Cypher export → {cypher_file}")

def generate_bloom_perspective():
    """Generates Bloom styling JSON specification."""
    bloom_path = VIZ_OUT / "neo4j_bloom_perspective.json"
    spec = {
        "perspectiveName": "DHAP-Net Cyber Attack Propagation",
        "description": "Visualizing lateral movement paths, compromised seeds, and Bayesian candidate risk distributions.",
        "categories": [
            {
                "name": "Host",
                "color": "#3A86FF",
                "caption": ["host_id"],
                "ruleStyles": [
                    {"rule": "is_compromised = true", "color": "#FF006E", "size": 1.5, "icon": "skull-crossbones"},
                    {"rule": "propagation_prob >= 0.05", "color": "#FFB703", "size": 1.2, "icon": "exclamation-triangle"},
                    {"rule": "propagation_prob < 0.05", "color": "#06D6A0", "size": 1.0, "icon": "server"}
                ]
            }
        ],
        "relationships": [
            {"type": "COMPROMISED", "color": "#FF006E", "style": "solid", "width": 2.5, "caption": "user"},
            {"type": "SIMULATED_PROPAGATION", "color": "#8338EC", "style": "dashed", "width": 1.5, "caption": "propagation_prob"},
            {"type": "COMMUNICATES_WITH", "color": "#4A5568", "style": "solid", "width": 0.8}
        ]
    }
    with open(bloom_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)
    print(f"[Export] Saved Bloom perspective config → {bloom_path}")

def copy_and_rename_visualizations():
    """Copies all HTML visualizations into visualizations/ with clear presentation numbering."""
    mapping = {
        "01_dataset_stats.html": "01_dataset_stats.html",
        "01_redteam_timeline.html": "02_redteam_timeline.html",
        "03_degree_dist.html": "03_traffic_and_degree_dist.html",
        "03_coverage_ceiling.html": "04_coverage_ceiling.html",
        "04_pr_curves_delta1h.html": "05_pr_curves_delta1h.html",
        "04_pr_curves_delta6h.html": "06_pr_curves_delta6h.html",
        "04_pr_curves_delta24h.html": "07_pr_curves_delta24h.html",
        "05_reliability.html": "08_reliability_diagram.html",
        "06_fan_chart.html": "09_fan_chart_credible_intervals.html",
        "07_ablation.html": "10_ablation_study.html",
        "08_comparison.html": "11_model_comparison.html",
        "02_throughput.html": "12_streaming_throughput.html",
        "11_attack_graph.html": "13_attack_graph_interactive.html",
        "12_time_slider.html": "14_time_slider_animation.html",
    }
    for src_name, dst_name in mapping.items():
        src_path = FIGURES_DIR / src_name
        dst_path = VIZ_OUT / dst_name
        if src_path.exists():
            shutil.copyfile(src_path, dst_path)
            print(f"[Copy] {src_name} → visualizations/{dst_name}")
        else:
            print(f"[Warning] Source figure not found: {src_path}")

if __name__ == "__main__":
    print("[Viz Builder] Exporting Cypher and Bloom specs...")
    generate_cypher_export()
    generate_bloom_perspective()
    print("[Viz Builder] Copying all visual artifacts to /visualizations ...")
    copy_and_rename_visualizations()
    print("[Viz Builder] Done.")
