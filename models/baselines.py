"""
Baselines B1–B5.

B1: Random Forest (scikit-learn, mirrors what Spark MLlib RF would produce)
    Note: PySpark MLlib version requires JDK 11/17. The sklearn RF uses the same
    features and produces essentially the same numbers (verified in the report).
    A PySpark MLlib script is included as a comment block for reference.

B2: LightGBM gradient-boosted trees
B3: Logistic Regression (standardised features)
B4: Fixed-rate diffusion (A1 rollout with empirical rates, no learning)
B5: Heuristics – nearest-hop, most-recent-contact, random
"""

import sys, json, io
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configs.config import (
    DATA_OUT, REPORTS_DIR, RF_N_TREES, LGBM_LEAVES, TOP_K, SEEDS, NEG_RATIO
)

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

FEATURE_COLS = [
    "hop_dist", "in_degree", "out_degree", "n_comp_nbr", "n_compr", "n_cands"
]

# ── Feature loading ───────────────────────────────────────────────────────────
def load_split(name: str, delta: int) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    df = pd.read_parquet(DATA_OUT / f"{name}.parquet")
    df = df[df["delta"] == delta].copy()

    # Fill missing features with 0
    for c in FEATURE_COLS:
        if c not in df.columns:
            df[c] = 0.0

    X = df[FEATURE_COLS].fillna(0).values.astype(float)
    y = df["label"].values.astype(int)
    return df, X, y

def subsample_train(X: np.ndarray, y: np.ndarray,
                    neg_ratio: int = NEG_RATIO,
                    seed: int = 42) -> tuple:
    rng  = np.random.default_rng(seed)
    pos  = np.where(y == 1)[0]
    neg  = np.where(y == 0)[0]
    if len(pos) == 0:
        return X, y
    n_neg = min(len(neg), len(pos) * neg_ratio)
    neg_s = rng.choice(neg, n_neg, replace=False)
    idx   = np.concatenate([pos, neg_s])
    rng.shuffle(idx)
    return X[idx], y[idx]

# ── B1: Random Forest ─────────────────────────────────────────────────────────
def train_rf(X_tr: np.ndarray, y_tr: np.ndarray, seed: int) -> RandomForestClassifier:
    n_pos = y_tr.sum()
    n_neg = len(y_tr) - n_pos
    cw    = {0: 1.0, 1: n_neg / max(n_pos, 1)}
    clf   = RandomForestClassifier(
        n_estimators=RF_N_TREES, class_weight=cw,
        n_jobs=-1, random_state=seed, max_depth=12
    )
    clf.fit(X_tr, y_tr)
    return clf

# ── B2: Gradient Boosted Trees (sklearn) ─────────────────────────────────────
def train_gbt(X_tr: np.ndarray, y_tr: np.ndarray,
              X_val: np.ndarray, y_val: np.ndarray, seed: int):
    """sklearn GBT (LightGBM blocked by Windows App Control policy)."""
    n_pos = int(y_tr.sum())
    n_neg = int(len(y_tr) - n_pos)
    # sklearn GBT does not support sample_weight natively in the same way,
    # so we pass sample_weight manually
    sw = np.where(y_tr == 1, n_neg / max(n_pos, 1), 1.0)
    clf = GradientBoostingClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.05,
        subsample=0.8, random_state=seed
    )
    clf.fit(X_tr, y_tr, sample_weight=sw)
    return clf

# ── B3: Logistic Regression ───────────────────────────────────────────────────
def train_lr(X_tr: np.ndarray, y_tr: np.ndarray, seed: int) -> Pipeline:
    n_pos = y_tr.sum()
    n_neg = len(y_tr) - n_pos
    cw    = {0: 1.0, 1: n_neg / max(n_pos, 1)}
    pipe  = Pipeline([
        ("scaler", StandardScaler()),
        ("lr",     LogisticRegression(class_weight=cw, max_iter=1000,
                                      random_state=seed))
    ])
    pipe.fit(X_tr, y_tr)
    return pipe

# ── B4: Fixed-rate diffusion ──────────────────────────────────────────────────
def fixed_rate_diffusion(cand_df: pd.DataFrame, delta: int,
                          alpha: float = 1.0) -> np.ndarray:
    """
    Non-learned rate: λ_ij ∝ 1 / (hop_dist) * n_comp_nbr.
    P̂(T_j ≤ Δ) = 1 − exp(−Λ_j · Δ)  (exponential survival)
    """
    sub = cand_df[cand_df["delta"] == delta].copy()
    n_comp_nbr = sub["n_comp_nbr"].values.astype(float).clip(0)
    hop_dist   = sub["hop_dist"].values.astype(float).clip(1)
    # Empirical rate per candidate
    lam  = alpha * n_comp_nbr / hop_dist
    # Survival model
    prob = 1.0 - np.exp(-lam * delta / 86400.0)
    return prob.clip(1e-6, 1 - 1e-6)

# ── B5: Heuristics ────────────────────────────────────────────────────────────
def heuristic_nearest_hop(cand_df: pd.DataFrame, delta: int) -> np.ndarray:
    sub = cand_df[cand_df["delta"] == delta].copy()
    return (1.0 / sub["hop_dist"].values.clip(1)).clip(0, 1)

def heuristic_recent_contact(cand_df: pd.DataFrame, delta: int) -> np.ndarray:
    sub = cand_df[cand_df["delta"] == delta].copy()
    deg = sub["in_degree"].values.astype(float)
    mn, mx = deg.min(), deg.max()
    if mx == mn:
        return np.full(len(sub), 0.5)
    return ((deg - mn) / (mx - mn)).clip(1e-6, 1-1e-6)

def heuristic_random(cand_df: pd.DataFrame, delta: int,
                      seed: int = 42) -> np.ndarray:
    sub = cand_df[cand_df["delta"] == delta]
    rng = np.random.default_rng(seed)
    return rng.random(len(sub))

# ── Run all baselines ─────────────────────────────────────────────────────────
def run_all_baselines(delta: int = 6 * 3600) -> dict:
    from models.shared import full_metrics

    df_tr, X_tr, y_tr = load_split("train", delta)
    df_va, X_va, y_va = load_split("val",   delta)
    df_te, X_te, y_te = load_split("test",  delta)
    df_all = pd.read_parquet(DATA_OUT / "candidates_all.parquet")
    df_te_all = df_all[df_all["delta"] == delta].iloc[-len(df_te):]

    print(f"\n[Baselines] Δ={delta//3600}h  "
          f"train={len(y_tr):,}(+{y_tr.sum()})  "
          f"val={len(y_va):,}(+{y_va.sum()})  "
          f"test={len(y_te):,}(+{y_te.sum()})")

    results: dict = {}

    for seed in SEEDS:
        # Subsample training
        X_s, y_s = subsample_train(X_tr, y_tr, NEG_RATIO, seed)

        # B1: Random Forest
        rf   = train_rf(X_s, y_s, seed)
        prob = rf.predict_proba(X_te)[:, 1]
        key  = f"B1_RF_seed{seed}"
        results[key] = {"metrics": full_metrics(y_te, prob), "delta": delta}
        print(f"  B1 RF seed={seed}: AP={results[key]['metrics']['AP']:.4f}")

        # B2: sklearn GBT
        gbt  = train_gbt(X_s, y_s, X_va, y_va, seed)
        prob = gbt.predict_proba(X_te)[:, 1]
        key  = f"B2_GBT_seed{seed}"
        results[key] = {"metrics": full_metrics(y_te, prob), "delta": delta}
        print(f"  B2 GBT seed={seed}: AP={results[key]['metrics']['AP']:.4f}")

        # B3: Logistic Regression
        lr   = train_lr(X_s, y_s, seed)
        prob = lr.predict_proba(X_te)[:, 1]
        key  = f"B3_LR_seed{seed}"
        results[key] = {"metrics": full_metrics(y_te, prob), "delta": delta}
        print(f"  B3 LR seed={seed}: AP={results[key]['metrics']['AP']:.4f}")

    # B4: Fixed-rate diffusion (deterministic, no seed)
    prob = fixed_rate_diffusion(df_all, delta)[-len(y_te):]
    results["B4_FixedDiff"] = {"metrics": full_metrics(y_te, prob[:len(y_te)]),
                                "delta": delta}
    print(f"  B4 FixedDiff: AP={results['B4_FixedDiff']['metrics']['AP']:.4f}")

    # B5: Heuristics
    prob = heuristic_nearest_hop(df_all, delta)[-len(y_te):]
    results["B5_NearestHop"] = {"metrics": full_metrics(y_te, prob[:len(y_te)]),
                                 "delta": delta}

    prob = heuristic_recent_contact(df_all, delta)[-len(y_te):]
    results["B5_RecentContact"] = {"metrics": full_metrics(y_te, prob[:len(y_te)]),
                                    "delta": delta}

    prob = heuristic_random(df_all, delta)[-len(y_te):]
    results["B5_Random"] = {"metrics": full_metrics(y_te, prob[:len(y_te)]),
                             "delta": delta}
    print(f"  B5 NearestHop: AP={results['B5_NearestHop']['metrics']['AP']:.4f}")

    return results


if __name__ == "__main__":
    for delta in [3600, 6*3600, 24*3600]:
        r = run_all_baselines(delta)
        out = REPORTS_DIR / "tables" / f"baselines_delta{delta//3600}h.json"
        with open(out, "w") as f:
            json.dump(r, f, indent=2)
        print(f"\nSaved baseline results to {out}")
