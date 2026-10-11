# DHAP-Net on LANL Cyber Data – Final Report

Generated: 2026-10-05 13:37


## 1. Download Ledger

| Timestamp | File | Bytes | Cumulative |
|-----------|------|-------|------------|
| 2026-10-05T07:20:44Z | lanl-2015/redteam.txt | 22,986 | 0.02 MB |
| 2026-10-05T07:24:16Z | lanl-2015/redteam.txt | 22,986 | 0.05 MB |
| 2026-10-05T07:32:50Z | lanl-2015/flows.txt [pilot] | 31,457,280 | 31.50 MB |
| 2026-10-05T08:07:47Z | lanl-2015/flows.txt [slice] | 1,733,391,808 | 1764.90 MB |

**Total downloaded:** 1.765 GB / 2.0 GB budget


**Tier used:** C  
(auth.txt estimated 0.00 GB for full slice; slice only covers red-team window + lead-in)


## 2. Dataset Statistics

- Red-team events: 20
- Distinct users: 20
- Distinct source hosts: 1
- Distinct destination hosts: 20
- Time range: 113,253 – 1,166,053 s
- Days in data: 1 – 13


### Coverage ceiling

| k | Recall upper bound |
|---|-------------------|
| 1 | 65.0% |
| 2 | 96.7% |
| 3 | 100.0% |

## 3. Design-to-implementation mapping


| Original design | What was built |
|-----------------|----------------|
| Kafka streaming | File-source replay in chronological 1-hour micro-batches |
| Spark Structured Streaming + HDFS | pandas streaming from local Parquet (HDFS stand-in) |
| PySpark MLlib RF | scikit-learn RF with identical features (Java/JDK not installed) |
| GraphFrames BFS | Python BFS over in-memory adjacency dict |
| PyTorch Geometric Temporal | Plain PyTorch (HRE+ST-DTE+BPD) |
| Plotly + Neo4j Bloom | Plotly + PyVis (Neo4j skipped – no local instance) |
| CVE nodes | Dropped (LANL has no CVE data) |
| IDS alerts | Red-team file used as attack signal and ground truth |
| Asset criticality | Dropped (graph-centrality proxy available but not used) |
| Organisation edges | Domain extracted from user@domain; cross-domain auth as proxy |
| Attack-type loss (α) | α=0 (no attack-type labels in LANL) |

**Note on PySpark:** JDK 11/17 is not installed on this machine.
The ETL logic is implemented in pandas with the same schema PySpark would produce.
The Spark MLlib RF baseline uses scikit-learn with identical feature columns.
All Parquet files are stored locally (stand-in for HDFS).
Throughput numbers describe the local machine only, not a cluster.


## 4. Results

| model            |   AP_mean |      AP_std |   ROC_AUC_mean |   P@10_mean |   R@10_mean |
|:-----------------|----------:|------------:|---------------:|------------:|------------:|
| A1               | 0.0189048 | 0.000159292 |       0.501301 |           0 |           0 |
| A2               | 0.0190174 | 0           |       0.5      |           0 |           0 |
| A3               | 0.0174625 | 0.00109948  |       0.447316 |           0 |           0 |
| B1_RF            | 0.0347731 | 0.00763662  |       0.578094 |           0 |           0 |
| B2_GBT           | 0.02645   | 0.00297461  |       0.600902 |           0 |           0 |
| B3_LR            | 0.0150933 | 0.000269998 |       0.383554 |           0 |           0 |
| B4_FixedDiff     | 0.0159468 | 0           |       0.357381 |           0 |           0 |
| B5_NearestHop    | 0.0160704 | 0           |       0.400444 |           0 |           0 |
| B5_Random        | 0.0155685 | 0           |       0.41357  |           0 |           0 |
| B5_RecentContact | 0.0266875 | 0           |       0.595921 |           0 |           0 |

## 5. Limitations

- **Single dataset:** Results describe one network and one red-team campaign.
  Generalisation is unknown.
- **Slice only:** We use only the red-team window plus a 2-day lead-in,
  not all 58 days. The graph is less dense than it would be over the full dataset.
- **Simplified reimplementations:** A2 (TGNE-TA-style) and A3 (DMSTG-AD-style)
  are implemented from short descriptions, not from the original authors' code.
  Their performance here may differ from the originals.
- **Spark in local mode:** PySpark was not available (JDK not installed).
  The ETL runs in pandas. Local Parquet stands in for HDFS.
  File-based replay stands in for Kafka.
- **Few positives:** The test set may have very few positive examples,
  making confidence intervals wide. Report bootstrap intervals where possible.
- **No GPU:** Training runs on CPU; wall times reflect a local workstation.


## 6. Reproducibility

```

python data/01_labels.py   # Step 0: labels (~5 KB)

python data/02_pilot.py    # Step 1: pilot read (~30 MB)

python data/03_fetch_slice.py  # Step 2: auth slice

python data/04_spark_etl.py    # Step 3: ETL

python data/06_candidates.py   # Step 3: candidates

python viz/eda_figs.py          # Step 4: EDA figures

python models/baselines.py      # Step 5: baselines

python train.py                 # Step 6: A1, A2, A3

python evaluate.py              # Step 7: metrics

python viz/result_figs.py       # Step 7: result figures

python viz/graph_view.py        # Step 7: graph view

python viz/build_dashboard.py   # Step 8: dashboard

```


Python: 3.14.5 (tags/v3.14.5:5607950, May 10 2026, 10:43:50) [MSC v.1944 64 bit (AMD64)]  

PyTorch: 2.12.0+cpu  

Seeds: 42, 123, 2024  
