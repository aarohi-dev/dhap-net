"""
evaluate.py – Aggregate all results, build final comparison tables,
ablation results, and calibration data.

Run: python evaluate.py
Reads from reports/tables/ and reports/data/
Writes: reports/tables/final_results.csv, ablation.csv, calibration.csv
"""

import sys, json, collections, io
from pathlib import Path
from itertools import product

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from configs.config import REPORTS_DIR, DATA_OUT, DELTAS, SEEDS, TOP_K

import numpy as np
import pandas as pd

# ── Aggregate training results ────────────────────────────────────────────────
def load_training_results() -> pd.DataFrame:
    p = REPORTS_DIR / "tables" / "training_results.json"
    if not p.exists():
        print("[Eval] No training_results.json found. Run train.py first.")
        return pd.DataFrame()
    with open(p) as f:
        data = json.load(f)

    rows = []
    for r in data:
        m = r["metrics"]
        row = {
            "model": r["model"].upper(),
            "delta_h": r["delta"] // 3600,
            "seed": r["seed"],
            "AP": m.get("AP", float("nan")),
            "ROC_AUC": m.get("ROC_AUC", float("nan")),
            "P@5": m.get("P@5", float("nan")),
            "R@5": m.get("R@5", float("nan")),
            "P@10": m.get("P@10", float("nan")),
            "R@10": m.get("R@10", float("nan")),
            "P@50": m.get("P@50", float("nan")),
            "R@50": m.get("R@50", float("nan")),
            "Brier": m.get("Brier", float("nan")),
            "CI_coverage": m.get("CI_coverage", float("nan")),
            "wall_time_s": r.get("wall_time_s", float("nan")),
            "best_val_ap": r.get("best_val_ap", float("nan")),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    return df

def load_baseline_results() -> pd.DataFrame:
    rows = []
    for delta in DELTAS:
        p = REPORTS_DIR / "tables" / f"baselines_delta{delta//3600}h.json"
        if not p.exists():
            continue
        with open(p) as f:
            data = json.load(f)
        for key, r in data.items():
            m = r["metrics"]
            # Parse model name and seed from key
            parts = key.split("_seed")
            model = parts[0]
            seed  = int(parts[1]) if len(parts) > 1 else 0
            row = {
                "model": model,
                "delta_h": delta // 3600,
                "seed": seed,
                "AP": m.get("AP", float("nan")),
                "ROC_AUC": m.get("ROC_AUC", float("nan")),
                "P@5": m.get("P@5", float("nan")),
                "R@5": m.get("R@5", float("nan")),
                "P@10": m.get("P@10", float("nan")),
                "R@10": m.get("R@10", float("nan")),
                "P@50": m.get("P@50", float("nan")),
                "R@50": m.get("R@50", float("nan")),
                "Brier": m.get("Brier", float("nan")),
                "CI_coverage": float("nan"),
                "wall_time_s": float("nan"),
                "best_val_ap": float("nan"),
            }
            rows.append(row)
    return pd.DataFrame(rows)

def aggregate_mean_std(df: pd.DataFrame, group_cols: list,
                       metric_cols: list) -> pd.DataFrame:
    """Return mean ± std over seeds."""
    rows = []
    for keys, grp in df.groupby(group_cols):
        row = dict(zip(group_cols, keys if isinstance(keys, tuple) else [keys]))
        for col in metric_cols:
            vals = grp[col].dropna().values
            row[f"{col}_mean"] = float(np.mean(vals)) if len(vals) > 0 else float("nan")
            row[f"{col}_std"]  = float(np.std(vals))  if len(vals) > 1 else 0.0
        rows.append(row)
    return pd.DataFrame(rows)

# ── Calibration data ──────────────────────────────────────────────────────────
def compute_calibration(model_name: str, delta_h: int, seed: int,
                         n_bins: int = 10) -> pd.DataFrame | None:
    p = (REPORTS_DIR / "data" /
         f"preds_{model_name.lower()}_delta{delta_h}h_seed{seed}.json")
    if not p.exists():
        return None
    with open(p) as f:
        d = json.load(f)
    probs  = np.array(d["probs"])
    labels = np.array(d["labels"])
    bins   = np.linspace(0, 1, n_bins + 1)
    rows   = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (probs >= lo) & (probs < hi)
        if mask.sum() == 0:
            continue
        rows.append({
            "model": model_name, "delta_h": delta_h, "seed": seed,
            "conf_lo": lo, "conf_hi": hi,
            "conf_mean": float(probs[mask].mean()),
            "acc": float(labels[mask].mean()),
            "n": int(mask.sum()),
        })
    return pd.DataFrame(rows)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    train_df    = load_training_results()
    baseline_df = load_baseline_results()

    metric_cols = ["AP","ROC_AUC","P@5","R@5","P@10","R@10","P@50","R@50","Brier"]

    # Final results table
    if not train_df.empty:
        agg_train = aggregate_mean_std(train_df, ["model","delta_h"], metric_cols)
    else:
        agg_train = pd.DataFrame()

    if not baseline_df.empty:
        agg_base = aggregate_mean_std(baseline_df, ["model","delta_h"], metric_cols)
    else:
        agg_base = pd.DataFrame()

    final = pd.concat([agg_train, agg_base], ignore_index=True)
    if not final.empty:
        final_path = REPORTS_DIR / "tables" / "final_results.csv"
        final.to_csv(final_path, index=False)
        print(f"[Eval] Final results table → {final_path}")
        print(final.to_string())

    # Calibration data
    cal_rows = []
    for model_name in ["a1", "a2", "a3"]:
        for delta_h in [1, 6, 24]:
            for seed in SEEDS:
                cal = compute_calibration(model_name, delta_h, seed)
                if cal is not None:
                    cal_rows.append(cal)
    if cal_rows:
        cal_df = pd.concat(cal_rows, ignore_index=True)
        cal_path = REPORTS_DIR / "tables" / "calibration.csv"
        cal_df.to_csv(cal_path, index=False)
        print(f"[Eval] Calibration data → {cal_path}")

    # Coverage ceiling
    ceiling_path = REPORTS_DIR / "coverage_ceiling.json"
    if ceiling_path.exists():
        with open(ceiling_path) as f:
            ceiling = json.load(f)
        print("\n── Coverage ceiling ──────────────────────────────────────")
        for k, v in ceiling.items():
            print(f"  k={k}: {v*100:.1f}%")

    # Throughput
    tp_path = REPORTS_DIR / "throughput.json"
    if tp_path.exists():
        with open(tp_path) as f:
            tp = json.load(f)
        print(f"\n── Throughput ────────────────────────────────────────────")
        print(f"  {tp.get('events_per_sec',0):,.0f} events/s")
        print(f"  {tp.get('ms_per_batch',0):.1f} ms/micro-batch")

    print("\n[Eval] ✓ Done.")

if __name__ == "__main__":
    main()
