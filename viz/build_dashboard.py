"""
Build the self-contained dashboard.html.
Embeds all individual figures into a single tabbed HTML file.

Run: python viz/build_dashboard.py
Output: reports/dashboard.html
"""

import sys, json, os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configs.config import REPORTS_DIR, FIGURES_DIR

FIGURE_DEFS = [
    ("01_redteam_timeline",   "1. Red-team timeline",          "EDA"),
    ("02_auth_types",         "2. Flows by protocol",          "EDA"),
    ("02b_logon_types",       "2b. Flows by top-10 src host",  "EDA"),
    ("03_degree_dist",        "3. Degree distribution",        "EDA"),
    ("04_pr_curves_delta1h",  "4. PR curves d=1h",             "Results"),
    ("04_pr_curves_delta6h",  "4. PR curves d=6h",             "Results"),
    ("04_pr_curves_delta24h", "4. PR curves d=24h",            "Results"),
    ("05_reliability",        "5. Reliability diagram",        "Results"),
    ("06_fan_chart",          "6. Fan chart (credible band)",  "Results"),
    ("07_ablation",           "7. Ablation (A1 variants)",     "Results"),
    ("08_comparison",         "8. Method comparison",          "Results"),
    ("10_throughput",         "10. Streaming throughput",      "Results"),
    ("11_attack_graph",       "11. Attack propagation graph",  "Graph"),
    ("12_time_slider",        "12. Risk evolution slider",     "Graph"),
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DHAP-Net on LANL Cyber Data – Dashboard</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Inter', sans-serif;
    background: linear-gradient(135deg, #0d0d1a 0%, #1a1a2e 50%, #16213e 100%);
    color: #e0e0e0;
    min-height: 100vh;
  }}
  header {{
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(255,255,255,0.1);
    padding: 1.5rem 2rem;
    position: sticky; top: 0; z-index: 100;
  }}
  header h1 {{
    font-size: 1.5rem; font-weight: 700;
    background: linear-gradient(90deg, #FF006E, #3A86FF, #8338EC);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }}
  header p {{ font-size: 0.85rem; color: #888; margin-top: 0.25rem; }}
  .tabs {{
    display: flex; gap: 0.5rem; padding: 1rem 2rem;
    background: rgba(0,0,0,0.2);
    border-bottom: 1px solid rgba(255,255,255,0.05);
    overflow-x: auto;
  }}
  .tab-btn {{
    padding: 0.5rem 1.2rem; border: none; border-radius: 20px;
    background: rgba(255,255,255,0.07); color: #aaa;
    cursor: pointer; font-size: 0.85rem; font-family: inherit;
    transition: all 0.2s;
  }}
  .tab-btn:hover {{ background: rgba(255,255,255,0.15); color: #fff; }}
  .tab-btn.active {{
    background: linear-gradient(90deg, #FF006E, #8338EC);
    color: #fff; font-weight: 600;
  }}
  .content {{ padding: 1.5rem 2rem; }}
  .section {{ display: none; }}
  .section.active {{ display: block; }}
  .fig-grid {{
    display: grid; grid-template-columns: 1fr;
    gap: 1.5rem;
  }}
  .fig-card {{
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px; overflow: hidden;
    backdrop-filter: blur(4px);
    transition: transform 0.2s, box-shadow 0.2s;
  }}
  .fig-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  }}
  .fig-card h3 {{
    padding: 0.8rem 1rem;
    font-size: 0.9rem; font-weight: 600;
    background: rgba(255,255,255,0.05);
    border-bottom: 1px solid rgba(255,255,255,0.06);
  }}
  iframe {{
    width: 100%; height: 600px; border: none;
    display: block;
  }}
  .summary-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem; margin-bottom: 1.5rem;
  }}
  .metric-card {{
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px; padding: 1rem;
    text-align: center;
  }}
  .metric-card .val {{
    font-size: 1.8rem; font-weight: 700;
    background: linear-gradient(90deg, #FF006E, #3A86FF);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }}
  .metric-card .label {{ font-size: 0.75rem; color: #888; margin-top: 0.3rem; }}
  .table-wrap {{ overflow-x: auto; }}
  table {{
    width: 100%; border-collapse: collapse;
    font-size: 0.82rem;
  }}
  th, td {{
    padding: 0.6rem 0.8rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    text-align: right;
  }}
  th {{ background: rgba(255,255,255,0.08); text-align: center; font-weight: 600; }}
  tr:hover td {{ background: rgba(255,255,255,0.04); }}
  .badge-a1 {{ color: #FF006E; font-weight: 700; }}
  .badge-a2 {{ color: #3A86FF; font-weight: 700; }}
  .badge-a3 {{ color: #8338EC; font-weight: 700; }}
  footer {{
    text-align: center; padding: 2rem;
    color: #555; font-size: 0.8rem;
    border-top: 1px solid rgba(255,255,255,0.05);
  }}
</style>
</head>
<body>
<header>
  <h1>⚡ DHAP-Net on LANL Cyber Data – Interactive Dashboard</h1>
  <p>Generated {timestamp} · Download budget: 2 GB · Data: LANL 2015 auth slice</p>
</header>

<div class="tabs">
  <button class="tab-btn active" onclick="showTab('overview')">Overview</button>
  <button class="tab-btn" onclick="showTab('eda')">EDA</button>
  <button class="tab-btn" onclick="showTab('results')">Results</button>
  <button class="tab-btn" onclick="showTab('graph')">Graph View</button>
  <button class="tab-btn" onclick="showTab('report')">Report</button>
</div>

<div class="content">
  <!-- OVERVIEW -->
  <div id="overview" class="section active">
    <div class="summary-grid">
      {summary_cards}
    </div>
    <div class="fig-card">
      <h3>📊 Final results table – Average Precision (Δ=6h)</h3>
      <div class="table-wrap">
        {results_table}
      </div>
    </div>
  </div>

  <!-- EDA -->
  <div id="eda" class="section">
    <div class="fig-grid">
      {eda_figs}
    </div>
  </div>

  <!-- RESULTS -->
  <div id="results" class="section">
    <div class="fig-grid">
      {result_figs}
    </div>
  </div>

  <!-- GRAPH -->
  <div id="graph" class="section">
    <div class="fig-grid">
      {graph_figs}
    </div>
  </div>

  <!-- REPORT -->
  <div id="report" class="section">
    {report_content}
  </div>
</div>

<footer>
  DHAP-Net / LANL Cyber · Python {python_version} · PyTorch · Plotly · PyVis
</footer>

<script>
function showTab(name) {{
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(name).classList.add('active');
  event.target.classList.add('active');
}}
</script>
</body>
</html>
"""

def fig_card(name: str, title: str) -> str:
    html_path = FIGURES_DIR / f"{name}.html"
    if not html_path.exists():
        return (f'<div class="fig-card"><h3>{title}</h3>'
                f'<p style="padding:1rem;color:#888;">Figure not yet generated. '
                f'Run the viz scripts first.</p></div>')
    # Embed as iframe with relative path
    rel = os.path.relpath(str(html_path), str(REPORTS_DIR))
    return (f'<div class="fig-card"><h3>{title}</h3>'
            f'<iframe src="{rel}" loading="lazy"></iframe></div>')

def results_table_html() -> str:
    p = REPORTS_DIR / "tables" / "final_results.csv"
    if not p.exists():
        return "<p style='padding:1rem;color:#888;'>Run evaluate.py to generate results.</p>"
    import csv
    rows = list(csv.DictReader(open(p)))
    if not rows:
        return "<p>No results yet.</p>"
    cols = ["model","delta_h","AP_mean","AP_std","ROC_AUC_mean","P@10_mean","R@10_mean"]
    cols = [c for c in cols if c in rows[0]]
    html = "<table><tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"
    for row in rows:
        html += "<tr>"
        for c in cols:
            val = row.get(c, "")
            try:
                val = f"{float(val):.4f}"
            except Exception:
                pass
            m = row.get("model","")
            cls = f'class="badge-{m.lower()}"' if m in ["A1","A2","A3"] else ""
            html += f"<td {cls}>{val}</td>"
        html += "</tr>"
    html += "</table>"
    return html

def summary_cards_html() -> str:
    items = []

    # Download budget
    p = REPORTS_DIR / "download_ledger.csv"
    if p.exists():
        import csv
        rows = list(csv.DictReader(open(p)))
        if rows:
            cum_gb = int(rows[-1]["cumulative_bytes"]) / 1e9
            items.append(("download-ledger", f"{cum_gb:.3f} GB", "Data downloaded"))

    # Red-team events
    rt_path = DATA_DIR if False else REPORTS_DIR.parent / "data" / "raw" / "redteam_labels.csv"
    if not rt_path.exists():
        rt_path = Path("data/raw/redteam_labels.csv")
    if rt_path.exists():
        import pandas as pd
        rt = pd.read_csv(str(rt_path))
        items.append(("events-total", f"{len(rt):,}", "Red-team events"))
        items.append(("hosts-compromised", f"{rt['dst'].nunique():,}", "Hosts compromised"))

    # Coverage ceiling
    cp = REPORTS_DIR / "coverage_ceiling.json"
    if cp.exists():
        ceiling = json.load(open(cp))
        items.append(("coverage-k2", f"{ceiling.get('2',0)*100:.0f}%", "Coverage ceiling k=2"))

    if not items:
        items = [
            ("budget", "2 GB", "Download budget"),
            ("status", "Step 0", "Current stage"),
        ]

    html = ""
    for (iid, val, label) in items:
        html += (f'<div class="metric-card" id="{iid}">'
                 f'<div class="val">{val}</div>'
                 f'<div class="label">{label}</div></div>')
    return html

def report_html() -> str:
    rmd = REPORTS_DIR / "report.md"
    if not rmd.exists():
        return "<p style='padding:2rem;color:#888;'>report.md not generated yet. Run the full pipeline first.</p>"
    text = rmd.read_text(encoding="utf-8")
    # Simple markdown → HTML (headings and paragraphs only)
    lines = []
    for line in text.split("\n"):
        if line.startswith("# "):
            lines.append(f"<h2>{line[2:]}</h2>")
        elif line.startswith("## "):
            lines.append(f"<h3>{line[3:]}</h3>")
        elif line.startswith("### "):
            lines.append(f"<h4>{line[4:]}</h4>")
        elif line.startswith("- "):
            lines.append(f"<li>{line[2:]}</li>")
        elif line.strip():
            lines.append(f"<p>{line}</p>")
    return (f'<div style="max-width:900px;padding:1.5rem;line-height:1.7;'
            f'color:#ccc;">' + "\n".join(lines) + "</div>")

def build():
    eda_figs = ""
    result_figs = ""
    graph_figs = ""
    for name, title, section in FIGURE_DEFS:
        card = fig_card(name, title)
        if section == "EDA":
            eda_figs += card
        elif section == "Results":
            result_figs += card
        else:
            graph_figs += card

    import sys as _sys
    html = HTML_TEMPLATE.format(
        timestamp    = datetime.now().strftime("%Y-%m-%d %H:%M"),
        summary_cards= summary_cards_html(),
        results_table= results_table_html(),
        eda_figs     = eda_figs,
        result_figs  = result_figs,
        graph_figs   = graph_figs,
        report_content = report_html(),
        python_version = _sys.version.split()[0],
    )

    out = REPORTS_DIR / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    print(f"[Dashboard] → {out}")
    print(f"[Dashboard] Open in browser: file:///{out.as_posix()}")

if __name__ == "__main__":
    build()
