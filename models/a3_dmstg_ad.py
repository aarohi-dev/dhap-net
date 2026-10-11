"""
A3 – DMSTG-AD-style Multi-Scale Spatio-Temporal GNN (simplified reimplementation).

Homogeneous host graph rebuilt per window with adaptive adjacency
A = softmax(H Hᵀ / sqrt(d)).
One or two GCN layers for space; dilated TCN (d=1,3,5) + BiGRU fused with
attention for time. Output per-node P(compromised within Δ). BCE.

Reference interpretation: simplified from multi-scale dynamic spatial-temporal
graph anomaly detection style.
"""

import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configs.config import D_HIDDEN, D_TIME, TCN_DILATIONS, DEVICE
from models.shared import Time2Vec, NodeMemory, DilatedTCN, adaptive_adjacency


class GCNLayer(nn.Module):
    def __init__(self, d_in: int, d_out: int):
        super().__init__()
        self.W = nn.Linear(d_in, d_out, bias=False)
        self.b = nn.Parameter(torch.zeros(d_out))

    def forward(self, H: torch.Tensor, A: torch.Tensor) -> torch.Tensor:
        """H: (N, d_in), A: (N, N) → (N, d_out)"""
        return F.relu(A @ self.W(H) + self.b)


class MultiScaleTemporalFusion(nn.Module):
    """Dilated TCN + BiGRU fused with learned attention weights."""
    def __init__(self, d: int = D_HIDDEN, dilations: list = TCN_DILATIONS):
        super().__init__()
        self.tcns = nn.ModuleList([DilatedTCN(d, d, dil) for dil in dilations])
        self.gru  = nn.GRU(d, d // 2, batch_first=True, bidirectional=True)
        n_streams = len(dilations) + 1
        self.attn = nn.Linear(d * n_streams, n_streams)
        self.fuse = nn.Linear(d * n_streams, d)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, T, d) → (B, d)"""
        xt = x.permute(0, 2, 1)   # (B, d, T)
        tcn_outs = [t(xt).mean(-1) for t in self.tcns]   # each (B, d)
        gru_out, _ = self.gru(x)
        gru_last   = gru_out[:, -1, :]                    # (B, d)
        all_streams = torch.cat(tcn_outs + [gru_last], dim=-1)   # (B, d*n)
        # Attention gate
        gates = torch.softmax(self.attn(all_streams), dim=-1)   # (B, n)
        # Weighted sum
        d = gru_last.shape[-1]
        streams_stacked = torch.stack(tcn_outs + [gru_last], dim=1)  # (B, n, d)
        weighted = (gates.unsqueeze(-1) * streams_stacked).sum(1)    # (B, d)
        return weighted


class DMSTGAD(nn.Module):
    """
    A3: Multi-Scale Spatio-Temporal GNN baseline.
    Window-level graph rebuilt with adaptive adjacency.
    """
    def __init__(self, d_hidden: int = D_HIDDEN, device: str = DEVICE):
        super().__init__()
        self.d_hidden = d_hidden
        self.device   = device

        self.gcn1    = GCNLayer(d_hidden, d_hidden)
        self.gcn2    = GCNLayer(d_hidden, d_hidden)
        self.temporal = MultiScaleTemporalFusion(d_hidden, TCN_DILATIONS)
        self.te      = Time2Vec(D_TIME)
        self.out_mlp = nn.Sequential(
            nn.Linear(d_hidden + D_TIME, d_hidden // 2),
            nn.ReLU(),
            nn.Linear(d_hidden // 2, 1),
        )
        self.memory   = NodeMemory(d_hidden, device)
        self.to(device)

    def forward(self, batch_data: dict, delta: float,
                pos_weight: float = 10.0, training: bool = True) -> dict:
        compr_idx = batch_data["compr_idx"]
        cand_idx  = batch_data["cand_idx"]
        n_compr   = len(compr_idx)
        n_cands   = len(cand_idx)

        if n_compr == 0 or n_cands == 0:
            dummy = torch.zeros(max(n_cands, 1), device=self.device)
            return {"prob": dummy, "loss": torch.tensor(0.0, device=self.device)}

        all_idx = compr_idx + cand_idx
        H       = self.memory.batch_get(all_idx).to(self.device)  # (C+N, d)

        # Adaptive adjacency
        A       = adaptive_adjacency(H, self.d_hidden)             # (C+N, C+N)

        # Two GCN layers
        H2 = self.gcn1(H, A)
        H2 = self.gcn2(H2, A)

        # Candidate slice
        h_cands = H2[n_compr:]                           # (N, d)

        # Multi-scale temporal fusion over the candidate histories
        # Use a 1-step "sequence" here (batch over candidates)
        seq = h_cands.unsqueeze(1)                       # (N, 1, d)
        h_fused = self.temporal(seq)                     # (N, d)

        # Delta encoding
        delta_t = torch.full((n_cands,), delta / 3600.0, device=self.device)
        te      = self.te(delta_t)                       # (N, D_TIME)

        logit = self.out_mlp(torch.cat([h_fused, te], dim=-1)).squeeze(-1)
        prob  = torch.sigmoid(logit).clamp(1e-6, 1-1e-6)

        out = {"prob": prob}

        if "label" in batch_data and training:
            y  = batch_data["label"].float().to(self.device)
            pw = torch.tensor([pos_weight], device=self.device)
            loss = F.binary_cross_entropy_with_logits(logit, y, pos_weight=pw)
            out["loss"] = loss

        return out

    def update_memory(self, node_idxs: list[int], new_hs: torch.Tensor):
        self.memory.batch_set(node_idxs, new_hs)
