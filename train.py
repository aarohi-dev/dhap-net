"""
train.py – Train A1, A2, A3 across all seeds with early stopping.

For each seed × model × delta:
  1. Overfit check on tiny subset (confirms loss falls).
  2. Full training with early stopping on validation AP.
  3. Save checkpoint and metrics.

Run: python train.py [--model a1|a2|a3|all] [--delta 1|6|24]
"""

import sys, argparse, json, time, os, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).resolve().parent))
from configs.config import (
    DATA_OUT, REPORTS_DIR, MODELS_DIR, SEEDS, EPOCHS, LR, EARLY_STOP,
    NEG_RATIO, DELTAS, DEVICE, D_HIDDEN, D_TIME, N_HEADS
)

import numpy as np
import pandas as pd
import torch
import torch.optim as optim
from models.shared import Vocabulary, NodeMemory, full_metrics
from models.a1_dhapnet import DHAPNet
from models.a2_tgne_ta import TGNETA
from models.a3_dmstg_ad import DMSTGAD

# ── Data helpers ──────────────────────────────────────────────────────────────
def load_candidates(name: str, delta: int) -> pd.DataFrame:
    df = pd.read_parquet(DATA_OUT / f"{name}.parquet")
    return df[df["delta"] == delta].reset_index(drop=True)

def build_batch(group: pd.DataFrame, vocab: Vocabulary,
                compr_times: dict, t: int,
                device: str = DEVICE) -> dict | None:
    """Convert a micro-batch group to a model-ready dict."""
    host_names  = group["host"].tolist()
    cand_idx    = [vocab[h] for h in host_names]
    compr_hosts = [h for h, tv in compr_times.items() if tv <= t]
    compr_idx   = [vocab[h] for h in compr_hosts]

    if not compr_idx or not cand_idx:
        return None

    labels = torch.tensor(group["label"].values, dtype=torch.float32, device=device)

    # delta_t for compromised nodes (t - T_v)
    dt_compr = torch.tensor(
        [float(t - compr_times.get(h, t)) for h in compr_hosts],
        dtype=torch.float32, device=device
    ).clamp(min=0)

    return {
        "compr_idx":    compr_idx,
        "cand_idx":     cand_idx,
        "label":        labels,
        "delta_t_compr": dt_compr,
        "edge_src":     [],
        "edge_dst":     [],
        "edge_rel":     torch.zeros(0, dtype=torch.long, device=device),
        "edge_feat":    torch.zeros(0, 8, device=device),
        "delta_t_edge": torch.zeros(0, device=device),
    }

# ── Overfit check ─────────────────────────────────────────────────────────────
def overfit_check(model, model_name: str, train_df: pd.DataFrame,
                  vocab: Vocabulary, compr_times: dict, delta: int):
    """Train on 50 rows to confirm loss decreases."""
    tiny = train_df.head(50)
    opt  = optim.Adam(model.parameters(), lr=1e-2)
    losses = []
    for _ in range(20):
        for t, grp in tiny.groupby("t"):
            batch = build_batch(grp, vocab, compr_times, int(t), DEVICE)
            if batch is None:
                continue
            model.train()
            out = model(batch, delta, training=True)
            if "loss" in out and out["loss"].requires_grad:
                opt.zero_grad()
                out["loss"].backward()
                opt.step()
                losses.append(out["loss"].item())
    if losses:
        print(f"  [{model_name}] Overfit check: loss {losses[0]:.4f} → {losses[-1]:.4f} "
              f"({'✓ decreasing' if losses[-1] < losses[0] else '✗ NOT decreasing'})")
    model.memory.reset()   # reset memory after overfit check

# ── Training loop ─────────────────────────────────────────────────────────────
def train_model(model_name: str, delta: int, seed: int):
    torch.manual_seed(seed)
    np.random.seed(seed)

    train_df = load_candidates("train", delta)
    val_df   = load_candidates("val",   delta)
    test_df  = load_candidates("test",  delta)

    # Build vocabulary from all hosts
    all_hosts = pd.read_parquet(DATA_OUT / "candidates_all.parquet")["host"].unique()
    vocab = Vocabulary()
    for h in all_hosts:
        vocab.add(h)
    vocab.freeze()

    # Load compromise times
    from configs.config import DATA_DIR
    rt_path = DATA_DIR / "redteam_labels.csv"
    if not rt_path.exists():
        # synthetic fallback: build from candidates_all
        cands_all = pd.read_parquet(DATA_OUT / "candidates_all.parquet")
        hosts = cands_all["host"].unique()
        comp_times_approx = {}
        for h in hosts:
            h_rows = cands_all[(cands_all["host"] == h) & (cands_all["label"] == 1)]
            if len(h_rows) > 0:
                comp_times_approx[h] = int(h_rows["t"].min())
        compr_times = comp_times_approx
    else:
        rt = pd.read_csv(rt_path)
        dst_first = rt.groupby("dst")["time"].min().to_dict()
        src_only  = set(rt["src"].unique()) - set(rt["dst"].unique())
        for h in src_only:
            dst_first[h] = int(rt[rt["src"] == h]["time"].min())
        compr_times = dst_first


    # Instantiate model
    n_rels = 5   # auth_NTLM_Interactive, auth_Kerberos_Network, user_logon, comm, dns_lookup
    if model_name == "a1":
        model = DHAPNet(n_relations=n_rels, device=DEVICE).to(DEVICE)
    elif model_name == "a2":
        model = TGNETA(device=DEVICE).to(DEVICE)
    else:
        model = DMSTGAD(device=DEVICE).to(DEVICE)

    model.memory = NodeMemory(D_HIDDEN, DEVICE)

    print(f"\n[Train] {model_name.upper()} | Δ={delta//3600}h | seed={seed}")
    overfit_check(model, model_name, train_df, vocab, compr_times, delta)

    opt = optim.Adam(model.parameters(), lr=LR)
    best_val_ap  = -1.0
    patience_cnt = 0
    history      = []
    # Initialise ckpt_path so it's always defined even if val never improves
    ckpt_path    = MODELS_DIR / f"{model_name}_delta{delta//3600}h_seed{seed}.pt"
    torch.save(model.state_dict(), ckpt_path)  # save initial weights as fallback

    t0_train = time.time()

    for epoch in range(EPOCHS):
        model.train()
        model.memory.reset()
        ep_loss = []

        # Micro-batch loop (by hour boundary)
        for t_val, grp in train_df.groupby("t"):
            batch = build_batch(grp, vocab, compr_times, int(t_val), DEVICE)
            if batch is None:
                continue
            out = model(batch, float(delta), training=True)
            if "loss" not in out or not out["loss"].requires_grad:
                continue
            opt.zero_grad()
            out["loss"].backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            ep_loss.append(out["loss"].item())

            # Update memory with new hidden state (use prob as proxy)
            if len(batch["cand_idx"]) > 0:
                new_h = out["prob"].detach().unsqueeze(-1).expand(
                    -1, D_HIDDEN) * 0.1   # minimal memory update
                model.update_memory(batch["cand_idx"], new_h)

        # Validation
        model.eval()
        val_probs, val_labels = [], []
        with torch.no_grad():
            for t_val, grp in val_df.groupby("t"):
                batch = build_batch(grp, vocab, compr_times, int(t_val), DEVICE)
                if batch is None:
                    continue
                out = model(batch, float(delta), training=False)
                val_probs.extend(out["prob"].cpu().numpy())
                val_labels.extend(batch["label"].cpu().numpy())

        val_ap = full_metrics(np.array(val_labels), np.array(val_probs))["AP"]
        mean_loss = float(np.mean(ep_loss)) if ep_loss else 0.0

        history.append({"epoch": epoch, "loss": mean_loss, "val_ap": val_ap})
        print(f"  Epoch {epoch+1:2d}/{EPOCHS}  loss={mean_loss:.4f}  val_AP={val_ap:.4f}")

        # NaN AP means no positives in val; treat as very small improvement to keep training
        effective_ap = val_ap if not np.isnan(val_ap) else -0.5

        if effective_ap > best_val_ap or epoch == 0:
            best_val_ap = effective_ap
            patience_cnt = 0
            torch.save(model.state_dict(), ckpt_path)
        else:
            patience_cnt += 1
            if patience_cnt >= EARLY_STOP and epoch >= 3:   # at least 3 epochs
                print(f"  Early stopping at epoch {epoch+1}")
                break

    wall_time = time.time() - t0_train
    print(f"[Train] Total time: {wall_time:.1f}s")

    # Test evaluation
    model.load_state_dict(torch.load(ckpt_path, map_location=DEVICE, weights_only=True))
    model.eval()
    model.memory.reset()

    test_probs, test_labels = [], []
    ci_lo_list, ci_hi_list  = [], []
    with torch.no_grad():
        for t_val, grp in test_df.groupby("t"):
            batch = build_batch(grp, vocab, compr_times, int(t_val), DEVICE)
            if batch is None:
                continue
            out = model(batch, float(delta), training=False)
            test_probs.extend(out["prob"].cpu().numpy())
            test_labels.extend(batch["label"].cpu().numpy())
            if "ci_lo" in out:
                ci_lo_list.extend(out["ci_lo"].cpu().numpy())
                ci_hi_list.extend(out["ci_hi"].cpu().numpy())

    y_te  = np.array(test_labels)
    p_te  = np.array(test_probs)
    metrics = full_metrics(y_te, p_te)

    # CI coverage for A1
    if ci_lo_list and model_name == "a1":
        from models.shared import ci_coverage
        metrics["CI_coverage"] = ci_coverage(y_te,
                                              np.array(ci_lo_list),
                                              np.array(ci_hi_list))

    print(f"\n[Test] {model_name.upper()} Δ={delta//3600}h seed={seed}:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    return {
        "model": model_name, "delta": delta, "seed": seed,
        "metrics": metrics, "history": history,
        "wall_time_s": wall_time,
        "best_val_ap": best_val_ap,
        "test_probs": p_te.tolist(),
        "test_labels": y_te.tolist(),
    }

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="all", choices=["a1","a2","a3","all"])
    parser.add_argument("--delta", default="all", choices=["1","6","24","all"])
    args = parser.parse_args()

    models = ["a1","a2","a3"] if args.model == "all" else [args.model]
    deltas = DELTAS if args.delta == "all" else [int(args.delta) * 3600]

    all_results = []
    for model_name in models:
        for delta in deltas:
            for seed in SEEDS:
                r = train_model(model_name, delta, seed)
                all_results.append(r)

    # Save results (without large arrays)
    out_path = REPORTS_DIR / "tables" / "training_results.json"
    slim = [{k: v for k, v in r.items()
             if k not in ("test_probs", "test_labels")}
            for r in all_results]
    with open(out_path, "w") as f:
        json.dump(slim, f, indent=2)
    print(f"\n[Train] Results saved to {out_path}")

    # Save full predictions for plotting
    for r in all_results:
        pred_path = (REPORTS_DIR / "data" /
                     f"preds_{r['model']}_delta{r['delta']//3600}h_seed{r['seed']}.json")
        with open(pred_path, "w") as f:
            json.dump({"probs": r["test_probs"], "labels": r["test_labels"]}, f)

if __name__ == "__main__":
    main()
