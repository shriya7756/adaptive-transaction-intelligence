"""
Behavioral Drift Detector — Compares P(current behavior | recent history)
against the customer's long-term baseline using KL divergence.

Detects "slow drift" anomalies: customer gradually shifting patterns
(domestic → international, low → high frequency) that Z-score alone misses.
"""

import math
from collections import defaultdict, deque
from typing import Optional
import numpy as np


def _kl_divergence(p: list[float], q: list[float]) -> float:
    """KL(P||Q) — 0 = identical distributions."""
    eps = 1e-9
    p = np.array(p, dtype=float) + eps
    q = np.array(q, dtype=float) + eps
    p /= p.sum()
    q /= q.sum()
    return float(np.sum(p * np.log(p / q)))


class _BehaviorWindow:
    """Stores the last N transactions' feature vectors for a customer."""

    def __init__(self, maxlen: int = 100):
        self.amounts:     deque = deque(maxlen=maxlen)
        self.hours:       deque = deque(maxlen=maxlen)
        self.categories:  deque = deque(maxlen=maxlen)
        self.cities:      deque = deque(maxlen=maxlen)
        self.is_new_devs: deque = deque(maxlen=maxlen)

    def push(self, tx: dict, behav: dict):
        self.amounts.append(float(tx["amount"]))
        self.hours.append(int(tx["timestamp"][11:13]))
        self.categories.append(tx["category"])
        self.cities.append(tx["city"])
        self.is_new_devs.append(int(behav.get("is_new_device", False)))


def _hour_dist(hours: list[int]) -> list[float]:
    """Convert list of hours to 24-bin probability vector."""
    counts = [0] * 24
    for h in hours:
        counts[h] += 1
    total = sum(counts) + 24   # Laplace smoothing
    return [(c + 1) / total for c in counts]


def _amount_dist(amounts: list[float], bins: int = 10, lo: float = 0, hi: float = 200_000) -> list[float]:
    counts, _ = np.histogram(amounts, bins=bins, range=(lo, hi))
    total = counts.sum() + bins
    return [(c + 1) / total for c in counts]


class BehavioralDriftDetector:
    """
    Per-customer recent-vs-baseline KL divergence for:
      - Amount distribution
      - Hour-of-day distribution
      - New-device rate
    Returns a drift_score 0–1.
    """

    def __init__(self):
        # Long-term baseline (large window)
        self._baseline: dict[str, _BehaviorWindow] = defaultdict(lambda: _BehaviorWindow(500))
        # Short-term recent window
        self._recent:   dict[str, _BehaviorWindow] = defaultdict(lambda: _BehaviorWindow(30))

    def score(self, transaction: dict, behav_features: dict) -> float:
        cid  = transaction["customer_id"]
        base = self._baseline[cid]
        rec  = self._recent[cid]

        n_base = len(base.amounts)
        n_rec  = len(rec.amounts)

        if n_base < 20 or n_rec < 5:
            # Not enough history to compute meaningful drift
            return 0.0

        # ── Amount KL divergence ──────────────────────────────────────────
        p_amt = _amount_dist(list(base.amounts))
        q_amt = _amount_dist(list(rec.amounts))
        kl_amt = _kl_divergence(q_amt, p_amt)

        # ── Hour KL divergence ────────────────────────────────────────────
        p_hr  = _hour_dist(list(base.hours))
        q_hr  = _hour_dist(list(rec.hours))
        kl_hr = _kl_divergence(q_hr, p_hr)

        # ── New device rate change ────────────────────────────────────────
        base_new_dev_rate = (sum(base.is_new_devs) + 1) / (n_base + 2)
        rec_new_dev_rate  = (sum(rec.is_new_devs)  + 1) / (n_rec  + 2)
        dev_drift = abs(rec_new_dev_rate - base_new_dev_rate)

        # ── Composite drift score ─────────────────────────────────────────
        # KL divergence can be large; normalise via sigmoid-like mapping
        kl_norm_amt = 1.0 - math.exp(-kl_amt * 2)
        kl_norm_hr  = 1.0 - math.exp(-kl_hr  * 2)

        drift_score = 0.40 * kl_norm_amt + 0.35 * kl_norm_hr + 0.25 * dev_drift

        # Push to windows AFTER computing (avoid contaminating own baseline)
        base.push(transaction, behav_features)
        rec.push(transaction,  behav_features)

        return round(float(min(drift_score, 1.0)), 4)

    def update(self, transaction: dict, behav_features: dict):
        """Explicit update (called by stream processor after scoring)."""
        # Pushed inside score() already; this is a no-op stub for API symmetry.
        pass
