"""
A2 – TGNE-TA-style Temporal Graph Transformer (simplified reimplementation).

Homogeneous host graph. Per-node Transformer aggregator over recent message
history with Time2Vec. MLP outputs P(j compromised within Δ). No diffusion,
no uncertainty. BCE with positive-class weighting.

Reference interpretation: simplified from "Temporal Graph Networks with
Temporal Attention" style models.
"""

import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configs.config import D_HIDDEN, D_TIME, N_HEADS, DEVICE
from models.shared import Time2Vec, NodeMemory

class TemporalTransformerAgg(nn.Module):
    """Transformer over incoming message history + Time2Vec."""
    def __init__(self, d_in: int, d_out: int, n_heads: int = N_HEADS,
                 max_seq: int = 32):
        super().__init__()
        self.te       = Time2Vec(D_TIME)
        self.proj_in  = nn.Linear(d_in + D_TIME, d_out)
        enc_layer     = nn.TransformerEncoderLayer(
            d_out, n_heads, dim_feedforward=d_out*2, batch_first=True, dropout=0.1
        )
        self.encoder  = nn.TransformerEncoder(enc_layer, num_layers=2)
        self.pool     = nn.Linear(d_out, d_out)

    def forward(self, h_seq: torch.Tensor, dt_seq: torch.Tensor) -> torch.Tensor:
        """
        h_seq:  (B, T, d_in)
        dt_seq: (B, T)         time deltas
        Returns (B, d_out)
        """
        te  = self.te(dt_seq.reshape(-1)).reshape(dt_seq.shape[0],
                                                   dt_seq.shape[1], -1)
        x   = torch.cat([h_seq, te], dim=-1)
        x   = self.proj_in(x)
        out = self.encoder(x)
        return self.pool(out.mean(1))


class TGNETA(nn.Module):
    """
    A2: Temporal-graph transformer baseline.
    All edge types collapsed to one (homogeneous).
    """
    def __init__(self, d_node: int = D_HIDDEN, d_hidden: int = D_HIDDEN,
                 n_heads: int = N_HEADS, device: str = DEVICE):
        super().__init__()
        self.d_hidden = d_hidden
        self.device   = device

        self.agg    = TemporalTransformerAgg(d_node, d_hidden, n_heads)
        self.te_mlp = Time2Vec(D_TIME)
        d_mlp_in    = 2 * d_hidden + D_TIME
        self.mlp    = nn.Sequential(
            nn.Linear(d_mlp_in, d_hidden),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(d_hidden, 1),
        )
        self.memory  = NodeMemory(d_hidden, device)
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

        h_compr = self.memory.batch_get(compr_idx).to(self.device)
        h_cands = self.memory.batch_get(cand_idx).to(self.device)

        # Aggregate compromised context
        h_c_agg = h_compr.mean(0, keepdim=True).expand(n_cands, -1)  # (N, d)

        # Δ encoding
        delta_t = torch.tensor([delta], device=self.device).expand(n_cands)
        te      = self.te_mlp(delta_t)   # (N, D_TIME)

        inp  = torch.cat([h_cands, h_c_agg, te], dim=-1)
        logit = self.mlp(inp).squeeze(-1)
        prob  = torch.sigmoid(logit)

        out = {"prob": prob.clamp(1e-6, 1-1e-6)}

        if "label" in batch_data and training:
            y  = batch_data["label"].float().to(self.device)
            pw = torch.tensor([pos_weight], device=self.device)
            loss = F.binary_cross_entropy_with_logits(logit, y,
                                                      pos_weight=pw)
            out["loss"] = loss
        return out

    def update_memory(self, node_idxs: list[int], new_hs: torch.Tensor):
        self.memory.batch_set(node_idxs, new_hs)
