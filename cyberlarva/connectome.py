"""Sparse connectome dynamics with an honest synthetic fallback.

The Winding et al. matrix supplies topology and synapse-count priors. Membrane
parameters, transmitter signs and the final muscle readout are model choices,
not measurements contained in the matrix.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import time
import numpy as np

try:
    from scipy import sparse
except ImportError:  # pragma: no cover
    sparse = None


MODALITIES = ("olfactory", "visual", "warm", "cold", "touch", "proprio", "noci")


@dataclass
class NeuralState:
    active: int
    mean_rate: float
    dn_rate: float
    step_ms: float
    source: str
    forward: float
    backward: float
    turn: float
    head_sweep: float


class ConnectomeBrain:
    def __init__(self, data_dir: Path, seed: int = 17):
        self.rng = np.random.default_rng(seed)
        self.source = "synthetic scaffold"
        self.n = 512
        self.W = None
        self.groups: dict[str, np.ndarray] = {}
        pack = data_dir / "winding_l1_connectome.npz"
        meta = data_dir / "groups.json"
        if pack.exists() and meta.exists() and sparse is not None:
            self.W = sparse.load_npz(pack).astype(np.float32).tocsr()
            raw = json.loads(meta.read_text(encoding="utf-8"))
            self.groups = {k: np.asarray(v, dtype=np.int32) for k, v in raw.items()}
            self.n = self.W.shape[0]
            self.source = "Winding L1 topology"
        else:
            # Deterministic sparse small-world scaffold keeps the demo usable
            # before the public supplementary data has been prepared.
            rows = self.rng.integers(0, self.n, 7000)
            cols = self.rng.integers(0, self.n, 7000)
            vals = self.rng.uniform(.04, .24, 7000).astype(np.float32)
            if sparse is not None:
                self.W = sparse.csr_matrix((vals, (cols, rows)), shape=(self.n, self.n))
            order = np.arange(self.n)
            self.groups = {m: order[i * 18:(i + 1) * 18] for i, m in enumerate(MODALITIES)}
            self.groups["dn_vnc"] = order[-96:]
        self.v = self.rng.normal(0, .02, self.n).astype(np.float32)
        self.rate = np.zeros(self.n, dtype=np.float32)
        self.refrac = np.zeros(self.n, dtype=np.int8)
        self.sign = np.where(self.rng.random(self.n) < .22, -1., 1.).astype(np.float32)
        self.bias = self.rng.uniform(.005, .025, self.n).astype(np.float32)
        self.t = 0.0
        self.last_spikes = np.zeros(self.n, dtype=np.float32)
        dn = self.groups.get("dn_vnc", np.arange(max(0, self.n - 96), self.n))
        self.dn = dn if len(dn) else np.arange(max(0, self.n - 96), self.n)
        # Reproducible experimental partitions; exposed as such in the UI.
        self.forward_dn = self.dn[0::4]
        self.backward_dn = self.dn[1::4]
        self.left_dn = self.dn[2::4]
        self.right_dn = self.dn[3::4]

    def reset(self):
        self.v.fill(0); self.rate.fill(0); self.refrac.fill(0); self.last_spikes.fill(0); self.t = 0

    def _indices(self, name: str) -> np.ndarray:
        aliases = {"warm": "thermo_warm", "cold": "thermo_cold", "touch": "mechano"}
        return self.groups.get(name, self.groups.get(aliases.get(name, ""), np.empty(0, dtype=np.int32)))

    def step(self, senses: dict[str, float], dt: float = .02) -> NeuralState:
        started = time.perf_counter()
        substeps = 4
        spikes = self.last_spikes
        for _ in range(substeps):
            syn = self.W @ (spikes * self.sign) if self.W is not None else 0
            drive = self.bias + np.asarray(syn, dtype=np.float32).reshape(-1) * .22
            for name in MODALITIES:
                idx = self._indices(name)
                if len(idx): drive[idx] += float(senses.get(name, 0)) * .65
            live = self.refrac <= 0
            self.v[live] = self.v[live] * .86 + drive[live]
            self.v += self.rng.normal(0, .012, self.n).astype(np.float32)
            spikes = (self.v > .5).astype(np.float32)
            self.v[spikes > 0] = 0
            self.refrac = np.maximum(self.refrac - 1, 0)
            self.refrac[spikes > 0] = 2
            self.rate = self.rate * .91 + spikes * 9.
        self.last_spikes = spikes
        self.t += dt
        def activity(idx): return float(np.mean(self.rate[idx])) if len(idx) else 0.
        f, b = activity(self.forward_dn), activity(self.backward_dn)
        l, r = activity(self.left_dn), activity(self.right_dn)
        # A segmental CPG supplies the rhythm; DN activity modulates it.
        odor = senses.get("olfactory", 0.)
        touch = senses.get("touch", 0.)
        forward = np.clip(.34 + odor * .42 + np.tanh(f * .18) * .2 - touch * .3, 0, 1)
        backward = np.clip(touch * .72 + senses.get("noci", 0.) * .45 + np.tanh(b * .18) * .12, 0, 1)
        turn = np.clip(senses.get("odor_lr", 0.) * 1.5 + (r - l) * .025 + senses.get("touch_lr", 0.) * 1.2, -1, 1)
        sweep = np.clip(.22 + (1 - odor) * .55 + abs(turn) * .25, 0, 1)
        return NeuralState(int(np.count_nonzero(self.rate > .5)), float(self.rate.mean()),
                           activity(self.dn), (time.perf_counter()-started)*1000, self.source,
                           float(forward), float(backward), float(turn), float(sweep))
