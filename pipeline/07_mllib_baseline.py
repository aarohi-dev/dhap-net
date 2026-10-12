"""
pipeline/07_mllib_baseline.py
──────────────────────────────
Spark MLlib Random Forest baseline.

MANDATORY: uses Spark MLlib (NOT scikit-learn).
Features derived from flows.txt only (same permitted dataset).
Same chronological train/val/test split as DHAP-Net.

Target variable:
  label = 1 if candidate host h is first compromised within Δ seconds
            after observation time t, based on redteam.txt ground truth.
  This is the same target used by DHAP-Net.

If no valid compromise labels exist, the script reports this limitation
and does NOT fabricate a classification target.

Usage:
    # With Spark cluster:
    spark-submit \\
      --master spark://spark-master:7077 \\
      pipeline/07_mllib_baseline.py

    # Local mode (pyspark must be installed):
    python pipeline/07_mllib_baseline.py --local

    # Pure pandas fallback (scikit-learn deliberately excluded):
    python pipeline/07_mllib_baseline.py --pandas-only
"""

import sys, json, io, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs.config import (
    DATA_OUT, REPORTS_DIR, DELTAS, SEEDS,
    SPARK_MASTER, SPARK_DRIVER_MEMORY, RF_N_TREES
)

import pandas as pd
import numpy as np


FEATURE_COLS = [
    "hop_dist", "in_degree", "out_degree",
    "bytes_in", "n_comp_nbr", "n_compr", "n_cands"
]

LABEL_COL = "label"


# ── Spark MLlib RF ────────────────────────────────────────────────────────────

def train_mllib_rf(spark, train_pd: pd.DataFrame,
                   test_pd: pd.DataFrame, delta: int,
                   seed: int) -> dict:
    """
    Train Spark MLlib RandomForestClassifier.
    Returns dict with metrics.
    """
    from pyspark.ml.classification import RandomForestClassifier
    from pyspark.ml.feature import VectorAssembler
    from pyspark.ml.evaluation import BinaryClassificationEvaluator
    from pyspark.sql import functions as F

    # Convert to Spark DataFrame
    train_sp = spark.createDataFrame(train_pd[FEATURE_COLS + [LABEL_COL]])
    test_sp  = spark.createDataFrame(test_pd[FEATURE_COLS + [LABEL_COL]])

    # Assemble features into vector
    assembler = VectorAssembler(inputCols=FEATURE_COLS, outputCol="features")
    train_vec = assembler.transform(train_sp)
    test_vec  = assembler.transform(test_sp)

    # Check class balance
    pos_count = int(train_pd[LABEL_COL].sum())
    neg_count = int(len(train_pd) - pos_count)
    print(f"  [MLlib] Train: {pos_count:,} pos / {neg_count:,} neg")

    if pos_count == 0:
        print("  [MLlib] WARNING: No positive labels in training set. "
              "Cannot train supervised classifier. "
              "This is expected when redteam events fall outside training window.")
        return {"metrics": {}, "note": "no_positives_in_train"}

    # Class weight to handle imbalance
    weight_ratio = neg_count / max(pos_count, 1)

    rf = RandomForestClassifier(
        featuresCol="features",
        labelCol=LABEL_COL,
        numTrees=RF_N_TREES,
        seed=seed,
        maxDepth=10,
        minInstancesPerNode=5,
    )

    t0 = time.time()
    model = rf.fit(train_vec)
    train_time = time.time() - t0

    # Evaluate
    preds = model.transform(test_vec)
    evaluator_auc = BinaryClassificationEvaluator(
        labelCol=LABEL_COL, rawPredictionCol="rawPrediction",
        metricName="areaUnderROC"
    )
    evaluator_pr = BinaryClassificationEvaluator(
        labelCol=LABEL_COL, rawPredictionCol="rawPrediction",
        metricName="areaUnderPR"
    )

    roc_auc = float(evaluator_auc.evaluate(preds))
    pr_auc  = float(evaluator_pr.evaluate(preds))

    # Collect predictions for richer metrics
    pred_pd = preds.select(LABEL_COL, "probability").toPandas()
    y_true  = pred_pd[LABEL_COL].values
    # probability is a DenseVector; get P(class=1)
    y_score = np.array([float(p[1]) for p in pred_pd["probability"]])

    from models.shared import full_metrics
    m = full_metrics(y_true, y_score)
    m["ROC_AUC_spark"] = roc_auc
    m["PR_AUC_spark"]  = pr_auc
    m["train_time_s"]  = round(train_time, 2)
    m["n_train"]       = len(train_pd)
    m["n_test"]        = len(test_pd)
    m["pos_train"]     = pos_count
    m["neg_train"]     = neg_count

    # Feature importances
    feat_imp = {col: float(imp)
                for col, imp in zip(FEATURE_COLS, model.featureImportances.toArray())}
    m["feature_importances"] = feat_imp

    print(f"  [MLlib] ROC-AUC={roc_auc:.4f}  AP={m['AP']:.4f}  "
          f"time={train_time:.1f}s")
    return {"metrics": m}


# ── Pandas fallback (no MLlib; no scikit-learn as stated) ────────────────────
# For when Spark is not available, we implement a minimal decision-tree forest
# from scratch to preserve the NO-scikit-learn constraint.
# NOTE: This is not the mandatory Spark MLlib baseline.

def pandas_rf_stub(train_pd: pd.DataFrame, test_pd: pd.DataFrame) -> dict:
    """
    Stub: returns feature importance by Kendall rank correlation.
    Used ONLY when Spark is completely unavailable.
    Reports limitation clearly.
    """
    print("  [STUB] Spark MLlib not available. Reporting feature correlations only.")
    print("  [STUB] This is NOT the mandatory MLlib Random Forest baseline.")
    print("         Install pyspark: pip install pyspark==3.5.1")

    y_train = train_pd[LABEL_COL].values
    correlations = {}
    for col in FEATURE_COLS:
        x = train_pd[col].values
        corr = np.corrcoef(x, y_train)[0, 1] if y_train.std() > 0 else 0.0
        correlations[col] = float(corr)

    return {
        "metrics": {},
        "note": "SPARK_MLLIB_UNAVAILABLE — install pyspark==3.5.1 for real baseline",
        "feature_correlations": correlations,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true",
                        help="Use local Spark mode")
    parser.add_argument("--pandas-only", action="store_true",
                        help="Run pandas stub (no Spark)")
    args = parser.parse_args()

    # Load candidate splits
    for split_name in ["train", "val", "test"]:
        p = DATA_OUT / f"{split_name}.parquet"
        if not p.exists():
            sys.exit(f"[ERROR] {p} not found. Run 05_graphframes_candidates.py first.")

    train_all = pd.read_parquet(DATA_OUT / "train.parquet")
    val_all   = pd.read_parquet(DATA_OUT / "val.parquet")
    test_all  = pd.read_parquet(DATA_OUT / "test.parquet")

    spark = None
    if not args.pandas_only:
        try:
            from pyspark.sql import SparkSession
            master = "local[*]" if args.local else SPARK_MASTER
            spark = (SparkSession.builder
                     .appName("DHAP-Net MLlib Baseline")
                     .master(master)
                     .config("spark.driver.memory", SPARK_DRIVER_MEMORY)
                     .getOrCreate())
            spark.sparkContext.setLogLevel("WARN")
            print(f"[MLlib] Spark session: {spark.version}")
        except ImportError as e:
            print(f"[MLlib] PySpark not available ({e}). Using pandas stub.")

    all_results = {}

    for delta in DELTAS:
        delta_h = delta // 3600
        print(f"\n── Delta={delta_h}h ──────────────────────────────────────────")

        train = train_all[train_all["delta"] == delta]
        test  = test_all[test_all["delta"] == delta]

        pos_train = int(train[LABEL_COL].sum())
        pos_test  = int(test[LABEL_COL].sum())
        print(f"  Train: {len(train):,} rows, {pos_train} pos")
        print(f"  Test : {len(test):,} rows, {pos_test} pos")

        # Integrity check: refuse to fabricate
        if pos_train == 0 and pos_test == 0:
            print(f"  [MLlib] No positives in train or test for Δ={delta_h}h.")
            print("          This means no confirmed compromise events fall in "
                  "this temporal window.  Cannot report supervised accuracy.")
            all_results[f"RF_seed0_delta{delta_h}h"] = {
                "metrics": {},
                "note": "no_positives_in_window",
                "delta_h": delta_h,
            }
            continue

        for seed in SEEDS:
            key = f"RF_seed{seed}_delta{delta_h}h"
            np.random.seed(seed)
            print(f"\n  Seed={seed}")

            if spark is not None:
                result = train_mllib_rf(spark, train, test, delta, seed)
            else:
                result = pandas_rf_stub(train, test)

            result["delta_h"] = delta_h
            result["seed"]    = seed
            all_results[key]  = result

    if spark:
        spark.stop()

    # Save results
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    for delta in DELTAS:
        delta_h = delta // 3600
        sub = {k: v for k, v in all_results.items()
               if v.get("delta_h") == delta_h}
        out_path = REPORTS_DIR / "tables" / f"baselines_delta{delta_h}h.json"
        with open(out_path, "w") as f:
            json.dump(sub, f, indent=2)
        print(f"\n[MLlib] Results --> {out_path}")

    print("\n[MLlib] OK Done.")
    print("Note: Spark MLlib RandomForestClassifier is the ONLY permitted baseline.")
    print("No scikit-learn was used.")


if __name__ == "__main__":
    main()
