"""
Shared utilities: node/edge encoding, Time2Vec, memory store,
feature extraction, and evaluation metrics.
"""

import sys
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configs.config import D_TIME, D_HIDDEN, DEVICE

# ── Time2Vec ──────────────────────────────────────────────────────────────────
class Time2Vec(nn.Module):
    """Learnable time encoding. Output dim = d_time."""
    def __init__(self, d: int = D_TIME):
        super().__init__()
        self.linear = nn.Linear(1, 1)
        self.periodic = nn.Linear(1, d - 1)

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        t = t.unsqueeze(-1).float()
        trend = self.linear(t)
        osc   = torch.sin(self.periodic(t))
        return torch.cat([trend, osc], dim=-1)   # (*, d_time)

# ── Host / edge vocabulary ────────────────────────────────────────────────────
class Vocabulary:
    """String → integer index mapping (grows dynamically)."""
    def __init__(self):
        self._tok: dict[str, int] = {"<PAD>": 0, "<UNK>": 1}
        self._frozen = False

    def __len__(self) -> int:
        return len(self._tok)

    def add(self, token: str) -> int:
        if token not in self._tok:
            if self._frozen:
                return self._tok["<UNK>"]
            self._tok[token] = len(self._tok)
        return self._tok[token]

    def __getitem__(self, token: str) -> int:
        return self._tok.get(token, self._tok["<UNK>"])

    def freeze(self):
        self._frozen = True

    def save(self, path: Path):
        import json
        with open(path, "w") as f:
            json.dump(self._tok, f)

    @classmethod
    def load(cls, path: Path) -> "Vocabulary":
        import json
        v = cls()
        with open(path) as f:
            v._tok = json.load(f)
        v._frozen = True
        return v

# ── Node memory store ─────────────────────────────────────────────────────────
class NodeMemory:
    """
    Stores the latest hidden state h_v(t) for each node.
    Updated incrementally per micro-batch (only touched nodes).
    """
    def __init__(self, d: int = D_HIDDEN, device: str = DEVICE):
        self.d = d
        self.device = device
        self._mem: dict[int, torch.Tensor] = {}   # node_idx → h vector

    def get(self, node_idx: int) -> torch.Tensor:
        if node_idx in self._mem:
            return self._mem[node_idx]
        return torch.zeros(self.d, device=self.device)

    def set(self, node_idx: int, h: torch.Tensor):
        self._mem[node_idx] = h.detach()

    def batch_get(self, idxs: list[int]) -> torch.Tensor:
        return torch.stack([self.get(i) for i in idxs])

    def batch_set(self, idxs: list[int], hs: torch.Tensor):
        for i, idx in enumerate(idxs):
            self.set(idx, hs[i])

    def reset(self):
        self._mem.clear()

# ── Dilated TCN block ─────────────────────────────────────────────────────────
class DilatedTCN(nn.Module):
    """Single dilated causal conv layer."""
    def __init__(self, d_in: int, d_out: int, dilation: int,
                 kernel_size: int = 3):
        super().__init__()
        pad = (kernel_size - 1) * dilation
        self.conv = nn.Conv1d(d_in, d_out, kernel_size,
                              dilation=dilation, padding=pad)
        self.d_out = d_out

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, d, T)
        out = self.conv(x)
        return out[..., :x.shape[-1]]  # trim causal padding

# ── Relation-typed adaptive adjacency ────────────────────────────────────────
def adaptive_adjacency(H: torch.Tensor, d_k: int) -> torch.Tensor:
    """A = softmax(H Hᵀ / sqrt(d_k)).  H: (N, d_k)"""
    scores = H @ H.T / (d_k ** 0.5)
    return F.softmax(scores, dim=-1)

# ── Evaluation metrics ────────────────────────────────────────────────────────
def average_precision(y_true: np.ndarray, y_score: np.ndarray) -> float:
    from sklearn.metrics import average_precision_score
    if y_true.sum() == 0:
        return float("nan")
    return float(average_precision_score(y_true, y_score))

def roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score
    if y_true.sum() == 0 or y_true.sum() == len(y_true):
        return float("nan")
    return float(roc_auc_score(y_true, y_score))

def precision_recall_at_k(y_true: np.ndarray, y_score: np.ndarray,
                           k: int) -> tuple[float, float]:
    idx = np.argsort(y_score)[::-1][:k]
    hits = y_true[idx].sum()
    prec = hits / k
    rec  = hits / max(y_true.sum(), 1)
    return float(prec), float(rec)

def brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    return float(np.mean((y_prob - y_true) ** 2))

def expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray,
                                n_bins: int = 10) -> float:
    bins = np.linspace(0, 1, n_bins + 1)
    ece  = 0.0
    n    = len(y_true)
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (y_prob >= lo) & (y_prob < hi)
        if mask.sum() == 0:
            continue
        acc  = y_true[mask].mean()
        conf = y_prob[mask].mean()
        ece += mask.sum() / n * abs(acc - conf)
    return float(ece)

def ci_coverage(y_true: np.ndarray, ci_lo: np.ndarray,
                ci_hi: np.ndarray) -> float:
    """Fraction of true values within the credible interval."""
    return float(np.mean((ci_lo <= y_true) & (y_true <= ci_hi)))

def bootstrap_ap(y_true: np.ndarray, y_score: np.ndarray,
                 n_boot: int = 1000, alpha: float = 0.05,
                 rng: Optional[np.random.Generator] = None
                 ) -> tuple[float, float, float]:
    """Returns (mean, lo, hi) bootstrap confidence interval for AP."""
    rng = rng or np.random.default_rng(42)
    scores = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(y_true), len(y_true))
        if y_true[idx].sum() == 0:
            continue
        scores.append(average_precision(y_true[idx], y_score[idx]))
    if not scores:
        return float("nan"), float("nan"), float("nan")
    scores = np.array(scores)
    return float(scores.mean()), float(np.percentile(scores, 100*alpha/2)), \
           float(np.percentile(scores, 100*(1-alpha/2)))

def full_metrics(y_true: np.ndarray, y_score: np.ndarray,
                 top_ks: list[int] = None) -> dict:
    from configs.config import TOP_K
    top_ks = top_ks or TOP_K
    m: dict = {}
    m["AP"]      = average_precision(y_true, y_score)
    m["ROC_AUC"] = roc_auc(y_true, y_score)
    m["Brier"]   = brier_score(y_true, (y_score - y_score.min()) /
                                (y_score.max() - y_score.min() + 1e-9))
    ap_mean, ap_lo, ap_hi = bootstrap_ap(y_true, y_score)
    m["AP_CI_lo"] = ap_lo
    m["AP_CI_hi"] = ap_hi
    for k in top_ks:
        p, r = precision_recall_at_k(y_true, y_score, k)
        m[f"P@{k}"] = p
        m[f"R@{k}"] = r
    return m
