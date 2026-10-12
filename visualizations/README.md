# DHAP-Net Matplotlib Visualization Suite

All visualizations have been generated using **Matplotlib** and **NetworkX** at **300 DPI** in publication-quality dark mode format (`#0B0F19`), saved directly as `.png` image files in both:
- **`visualizations/`** (Root folder)
- **`visualizations/png/`** (Dedicated PNG gallery folder)

---

## 🖼️ Catalog of Matplotlib PNG Visualizations

| Image File | PPT Content Reference | Description |
| :--- | :--- | :--- |
| **[`01_dataset_stats.png`](file:///e:/GitHub/dhap-net/visualizations/01_dataset_stats.png)** | §1 & §5: Dataset Overview & Compaction | Protocol share pie chart (TCP 89.67%, UDP 7.77%, ICMP 2.56%) alongside 88.6% ETL volume compaction (130M raw flows to 14.8M aggregated edges). |
| **[`02_redteam_timeline.png`](file:///e:/GitHub/dhap-net/visualizations/02_redteam_timeline.png)** | §1: Ground-Truth Attacks | Timeline of 749 confirmed red-team lateral movement events and daily compromised target host counts across 36 observation days. |
| **[`03_degree_distribution.png`](file:///e:/GitHub/dhap-net/visualizations/03_degree_distribution.png)** | §5: Network Composition | Log-log power-law in-degree and out-degree host distributions in enterprise LANL traffic ($\gamma \approx 1.65$). |
| **[`04_coverage_ceiling.png`](file:///e:/GitHub/dhap-net/visualizations/04_coverage_ceiling.png)** | §5: Reachability Ceiling | Theoretical recall upper bound vs BFS hop expansion ($k=1$: 19.26%, $k=2$: 49.18%, $k=3$: 49.18%). |
| **[`05_pr_curves_delta1h.png`](file:///e:/GitHub/dhap-net/visualizations/05_pr_curves_delta1h.png)** | §7: Classification Results ($\Delta = 1\text{h}$) | Precision-Recall curves under extreme class imbalance (<0.08% positive rate) for 1-hour prediction horizon. |
| **[`06_pr_curves_delta6h.png`](file:///e:/GitHub/dhap-net/visualizations/06_pr_curves_delta6h.png)** | §7: Classification Results ($\Delta = 6\text{h}$) | Precision-Recall curves for 6-hour prediction horizon ($\text{AP} = 0.0189$). |
| **[`07_pr_curves_delta24h.png`](file:///e:/GitHub/dhap-net/visualizations/07_pr_curves_delta24h.png)** | §7: Classification Results ($\Delta = 24\text{h}$) | Long-term 24-hour horizon PR curves showing 17.1× performance scaling ($\text{AP} = 0.0547$). |
| **[`08_reliability_diagram.png`](file:///e:/GitHub/dhap-net/visualizations/08_reliability_diagram.png)** | §6 & §7: Probability Calibration | Reliability diagram comparing predicted probabilities against observed empirical compromise frequencies (Brier score = 0.2053). |
| **[`09_fan_chart_credible_intervals.png`](file:///e:/GitHub/dhap-net/visualizations/09_fan_chart_credible_intervals.png)** | §6: Gillespie MC Rollouts | Continuous-time lateral movement arrival forecast with shaded 90% Bayesian Credible Intervals $[\hat{p}_{\text{lo}}, \hat{p}_{\text{hi}}]$. |
| **[`10_ablation_study.png`](file:///e:/GitHub/dhap-net/visualizations/10_ablation_study.png)** | §7: Component Contributions | Horizontal bar chart demonstrating degradation when removing BPD Head, HRE, Node Memory, Bayesian Diffusion, or Multi-Scale TCN. |
| **[`11_model_comparison.png`](file:///e:/GitHub/dhap-net/visualizations/11_model_comparison.png)** | §8: Benchmark Model Comparison | Benchmark comparison of DHAP-Net vs Spark MLlib Random Forest, LightGBM, Logistic Regression, and Heuristics. |
| **[`12_streaming_throughput.png`](file:///e:/GitHub/dhap-net/visualizations/12_streaming_throughput.png)** | §4: Stream Ingestion Performance | Apache Kafka replay rate stability (>560,000 records/sec) and micro-batch latency breakdown (<0.88 ms/batch). |
| **[`13_attack_propagation_graph.png`](file:///e:/GitHub/dhap-net/visualizations/13_attack_propagation_graph.png)** | §3 & §8: Attack Propagation Topology | NetworkX graph visualization showing compromised footholds (stars), 1-hop and 2-hop target candidates, and lateral movement attack pathways. |
| **[`14_neo4j_bloom_topology_view.png`](file:///e:/GitHub/dhap-net/visualizations/14_neo4j_bloom_topology_view.png)** | §8 & §11: Neo4j Bloom Perspective | Graph canvas simulating Neo4j Bloom styling with halo glyphs, relationship types, and side inspector panel. |
| **[`15_time_slider_snapshots.png`](file:///e:/GitHub/dhap-net/visualizations/15_time_slider_snapshots.png)** | §8: Temporal Dynamics | Multi-panel micro-batch snapshot ($T=6\text{h}, 12\text{h}, 18\text{h}, 24\text{h}$) capturing attack propagation across time. |

---

## 🔁 How to Re-generate All Matplotlib PNGs

To re-run and re-generate all 15 figures programmatically at any time:

```powershell
python generate_all_matplotlib_figs.py
```
