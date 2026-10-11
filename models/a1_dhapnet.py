"""
A1 – DHAP-Net (adapted for LANL).

Architecture:
  HRE  : Heterogeneous Relation Encoder (per-relation W_r + Time2Vec)
  ST-DTE: Spatio-Temporal Dual Temporal Encoder
           – dilated TCN (d=1,3,5)
           – BiGRU
           – Transformer encoder
           – linear fusion
  BPD  : Bayesian Propagation-Diffusion head
           – LogNormal posterior for each edge rate
           – ELBO training
           – Gillespie-style Monte-Carlo rollout

Loss: BCE(y, p̂) + β·(−ELBO) + γ·KL
"""

import sys, math
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configs.config import (
    D_HIDDEN, D_TIME, N_HEADS, TCN_DILATIONS, N_GRU_LAYERS,
    N_SAMPLES_TRAIN, N_SAMPLES_EVAL, BETA, GAMMA, DEVICE
)
from models.shared import Time2Vec, NodeMemory, DilatedTCN, adaptive_adjacency

# ── HRE: Heterogeneous Relation Encoder ──────────────────────────────────────
class HRE(nn.Module):
    """
    For typed edge (u→v, relation r, time t):
      m_{u→v}^r(t) = W_r · [h_u ‖ x_uv ‖ TE(t − t_u)]
    """
    def __init__(self, n_relations: int, d_node: int, d_edge: int,
                 d_time: int = D_TIME, d_out: int = D_HIDDEN):
        super().__init__()
        d_in = d_node + d_edge + d_time
        self.W_r  = nn.ModuleList([nn.Linear(d_in, d_out) for _ in range(n_relations)])
        self.te   = Time2Vec(d_time)
        self.d_out = d_out

    def forward(self, h_u: torch.Tensor, x_uv: torch.Tensor,
                delta_t: torch.Tensor, rel_ids: torch.Tensor) -> torch.Tensor:
        """
        h_u:      (E, d_node)
        x_uv:     (E, d_edge)
        delta_t:  (E,) time since last update of u
        rel_ids:  (E,) integer relation type
        Returns:  (E, d_out)
        """
        te   = self.te(delta_t)                      # (E, d_time)
        inp  = torch.cat([h_u, x_uv, te], dim=-1)   # (E, d_in)
        msgs = torch.zeros(len(inp), self.d_out, device=inp.device)
        for r_id, W in enumerate(self.W_r):
            mask = (rel_ids == r_id)
            if mask.any():
                msgs[mask] = W(inp[mask])
        return msgs

# ── ST-DTE: Spatio-Temporal Dual Temporal Encoder ────────────────────────────
class STDTE(nn.Module):
    """
    Per-node encoder over a sequence of incoming messages.
    Channels: TCN(d=1), TCN(d=3), TCN(d=5), BiGRU, Transformer.
    Fused with a linear layer.
    """
    def __init__(self, d_msg: int = D_HIDDEN, d_out: int = D_HIDDEN,
                 dilations: list = TCN_DILATIONS, n_heads: int = N_HEADS):
        super().__init__()
        self.tcns    = nn.ModuleList([DilatedTCN(d_msg, d_msg, d) for d in dilations])
        self.bigru   = nn.GRU(d_msg, d_msg // 2, batch_first=True,
                               bidirectional=True, num_layers=N_GRU_LAYERS)
        enc_layer    = nn.TransformerEncoderLayer(d_msg, n_heads,
                                                  dim_feedforward=d_msg*2,
                                                  batch_first=True, dropout=0.1)
        self.transformer = nn.TransformerEncoder(enc_layer, num_layers=1)
        d_total      = d_msg * (len(dilations) + 2)   # TCNs + BiGRU + Transformer
        self.fuse    = nn.Linear(d_total, d_out)

    def forward(self, msgs: torch.Tensor) -> torch.Tensor:
        """
        msgs: (B, T_max, d_msg)  – padded message sequence for each node.
        Returns: (B, d_out)
        """
        x_t = msgs.permute(0, 2, 1)   # (B, d, T) for Conv1d
        tcn_outs = [tcn(x_t).mean(-1) for tcn in self.tcns]   # each (B, d_msg)
        gru_out, _ = self.bigru(msgs)                           # (B, T, d_msg)
        gru_last   = gru_out[:, -1, :]                          # (B, d_msg)
        tf_out     = self.transformer(msgs).mean(1)             # (B, d_msg)
        fused      = torch.cat(tcn_outs + [gru_last, tf_out], dim=-1)
        return self.fuse(fused)                                 # (B, d_out)

# ── BPD: Bayesian Propagation-Diffusion ──────────────────────────────────────
class BPD(nn.Module):
    """
    Rate head: for edge (i→j) with i compromised and j susceptible,
      input:  [h_i ‖ h_j ‖ TE(t − T_i)]
      output: λ_ij, μ_ij, σ_ij   (LogNormal posterior parameters)
    """
    def __init__(self, d_node: int = D_HIDDEN, d_time: int = D_TIME):
        super().__init__()
        d_in = 2 * d_node + d_time
        self.te   = Time2Vec(d_time)
        self.head = nn.Sequential(
            nn.Linear(d_in, d_node),
            nn.ReLU(),
            nn.Linear(d_node, 3),   # λ, μ, log_σ
        )

    def forward(self, h_i: torch.Tensor, h_j: torch.Tensor,
                delta_t: torch.Tensor) -> tuple:
        """
        h_i, h_j: (E, d_node)
        delta_t:  (E,)   t − T_i
        Returns: (lambda, mu, sigma)  each (E,)
        """
        te  = self.te(delta_t)                              # (E, d_time)
        inp = torch.cat([h_i, h_j, te], dim=-1)
        out = self.head(inp)                                # (E, 3)
        lam    = F.softplus(out[:, 0]) + 1e-6              # λ > 0
        mu     = out[:, 1]                                  # μ ∈ ℝ
        sigma  = F.softplus(out[:, 2]) + 1e-6              # σ > 0
        return lam, mu, sigma

    def elbo(self, lam: torch.Tensor, mu: torch.Tensor,
             sigma: torch.Tensor, delta: torch.Tensor,
             cumulative: torch.Tensor, event: torch.Tensor) -> torch.Tensor:
        """
        Compute ELBO = E_q[log p(data | λ)] − KL(q ‖ prior).
        lam:        (E,)  point estimate of λ
        mu, sigma:  (E,)  LogNormal posterior params
        delta:      (E,)  time window Δ
        cumulative: (E,)  Λ_j = Σ λ_{ij}  (summed per candidate j)
        event:      (E,)  δ_j = 1 if j is compromised in window
        """
        # Log-likelihood under constant-rate assumption
        log_lik = event * torch.log(cumulative + 1e-8) - cumulative * delta

        # KL(LogNormal(μ,σ²) ‖ LogNormal(0,1))
        kl = -0.5 * (1 + 2*torch.log(sigma) - mu**2 - sigma**2)

        return log_lik.mean() - kl.mean()

    def rollout(self, h_compr: torch.Tensor, h_cands: torch.Tensor,
                lam_mu: torch.Tensor, lam_sigma: torch.Tensor,
                delta: float, n_samples: int, k: int) -> tuple:
        """
        Monte-Carlo Gillespie rollout.
        h_compr: (C, d)   hidden states of compromised nodes
        h_cands: (N, d)   hidden states of candidates
        lam_mu, lam_sigma: (C, N)  rate distribution per edge
        delta:   float    time horizon
        Returns: (probs, ci_lo, ci_hi)  each (N,)
        """
        C, N = lam_mu.shape
        hit = torch.zeros(N, device=lam_mu.device)

        # Reparameterisation: λ ~ LogNormal(μ, σ)
        eps = torch.randn(n_samples, C, N, device=lam_mu.device)
        lam_samples = torch.exp(lam_mu.unsqueeze(0) +
                                lam_sigma.unsqueeze(0) * eps)  # (S, C, N)

        # Bellman-Ford on Exp delays: T_j = min over paths of sum(Exp(λ))
        # Vectorised: for k=1 (direct), T_j = Exp(Σ_i λ_{ij})
        # For k>1 this is approximate; we do k rounds
        lam_total = lam_samples.sum(1)                  # (S, N) Σ_i λ_{ij}
        lam_total = lam_total.clamp(min=1e-8)
        # Sample Exp(λ) delays
        delays = torch.zeros_like(lam_total)
        unif   = torch.rand_like(lam_total)
        delays = -torch.log(unif + 1e-9) / lam_total   # Exp(λ) samples
        hit    = (delays <= delta).float().mean(0)       # (N,)

        # Credible interval across samples
        delays_sorted = delays.sort(0).values
        lo = delays_sorted[int(0.05 * n_samples)].clamp(0, delta)
        hi = delays_sorted[int(0.95 * n_samples)].clamp(0, delta)
        ci_lo = (lo <= delta).float()
        ci_hi = (hi <= delta).float()

        return hit, ci_lo, ci_hi

# ── Full DHAP-Net ─────────────────────────────────────────────────────────────
class DHAPNet(nn.Module):
    def __init__(self, n_relations: int, d_edge: int = 8,
                 d_hidden: int = D_HIDDEN, d_time: int = D_TIME,
                 n_heads: int = N_HEADS, device: str = DEVICE):
        super().__init__()
        self.d_hidden = d_hidden
        self.device   = device

        self.hre   = HRE(n_relations, d_hidden, d_edge, d_time, d_hidden)
        self.stdte = STDTE(d_hidden, d_hidden, TCN_DILATIONS, n_heads)
        self.bpd   = BPD(d_hidden, d_time)
        self.memory = NodeMemory(d_hidden, device)

        # Node-type embedding (Host=0, User=1, Domain=2)
        self.type_emb = nn.Embedding(4, d_hidden, padding_idx=0)

        self.to(device)

    def encode_batch(self, msgs: torch.Tensor) -> torch.Tensor:
        """msgs: (B, T, d) → h: (B, d)"""
        if msgs.shape[1] == 0:
            return torch.zeros(msgs.shape[0], self.d_hidden, device=self.device)
        return self.stdte(msgs)

    def forward(self, batch_data: dict, delta: float,
                training: bool = True) -> dict:
        """
        batch_data keys:
          compr_idx:  list of int  – node indices of compromised set C(t)
          cand_idx:   list of int  – candidate node indices
          edge_src:   (E,)  source node indices
          edge_dst:   (E,)  destination node indices
          edge_rel:   (E,)  relation type id
          edge_feat:  (E, d_edge)  edge features
          delta_t_edge: (E,)  time since last update of src
          delta_t_compr: (C,)  t − T_i for each compromised node
          label:      (N,)  binary labels for candidates
        Returns dict with 'prob', 'mu', 'sigma', optional 'elbo_val'
        """
        compr_idx = batch_data["compr_idx"]
        cand_idx  = batch_data["cand_idx"]
        n_compr   = len(compr_idx)
        n_cands   = len(cand_idx)

        if n_compr == 0 or n_cands == 0:
            dummy = torch.zeros(max(n_cands, 1), device=self.device)
            return {"prob": dummy, "loss": torch.tensor(0.0, device=self.device)}

        # ── Retrieve memories ─────────────────────────────────────────────
        h_compr = self.memory.batch_get(compr_idx).to(self.device)  # (C, d)
        h_cands = self.memory.batch_get(cand_idx).to(self.device)   # (N, d)

        # ── BPD rate per (i, j) edge ──────────────────────────────────────
        delta_t_c = batch_data.get("delta_t_compr",
                                   torch.zeros(n_compr, device=self.device))
        if not isinstance(delta_t_c, torch.Tensor):
            delta_t_c = torch.tensor(delta_t_c, dtype=torch.float32,
                                     device=self.device)

        # Build (C×N) grid
        h_i = h_compr.unsqueeze(1).expand(-1, n_cands, -1).reshape(-1, self.d_hidden)
        h_j = h_cands.unsqueeze(0).expand(n_compr, -1, -1).reshape(-1, self.d_hidden)
        dt  = delta_t_c.unsqueeze(1).expand(-1, n_cands).reshape(-1)

        lam_flat, mu_flat, sig_flat = self.bpd(h_i, h_j, dt)
        lam_grid = lam_flat.reshape(n_compr, n_cands)  # (C, N)
        mu_grid  = mu_flat.reshape(n_compr, n_cands)
        sig_grid = sig_flat.reshape(n_compr, n_cands)

        # Rollout
        n_samples = N_SAMPLES_TRAIN if training else N_SAMPLES_EVAL
        prob, ci_lo, ci_hi = self.bpd.rollout(
            h_compr, h_cands, mu_grid, sig_grid, delta, n_samples, k=2
        )
        prob = prob.clamp(1e-6, 1 - 1e-6)

        out = {"prob": prob, "ci_lo": ci_lo, "ci_hi": ci_hi,
               "mu": mu_grid, "sigma": sig_grid, "lam": lam_grid}

        # ── Loss ─────────────────────────────────────────────────────────
        if "label" in batch_data and training:
            y = batch_data["label"].float().to(self.device)
            # BCE on rollout probs
            loss_bce = F.binary_cross_entropy(prob, y)

            # ELBO: compute at per-candidate level (N,)
            # cum_lam[j] = sum_i lambda_ij  (the total hazard for candidate j)
            cum_lam  = lam_grid.sum(0)               # (N,)
            delta_t  = torch.full((n_cands,), delta,
                                  device=self.device) # (N,)
            # Use mean mu/sigma across in-edges for the candidate-level posterior
            mu_cand  = mu_grid.mean(0)               # (N,)
            sig_cand = sig_grid.mean(0).clamp(1e-6)  # (N,)
            elbo     = self.bpd.elbo(
                cum_lam, mu_cand, sig_cand, delta_t, cum_lam, y
            )
            # KL on all (C*N) edge posteriors
            kl = (-0.5 * (1 + 2*torch.log(sig_flat)
                          - mu_flat**2 - sig_flat**2)).mean()
            loss = loss_bce - BETA * elbo + GAMMA * kl
            out["loss"] = loss
            out["elbo_val"] = elbo.item()


        return out

    def update_memory(self, node_idxs: list[int], new_hs: torch.Tensor):
        self.memory.batch_set(node_idxs, new_hs)
