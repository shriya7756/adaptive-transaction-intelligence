"""
Statistical Anomaly Detector — Amount and velocity statistical signals.

Uses:
  - Z-score against customer baseline
  - IQR-based outlier detection
  - Isolation Forest (fitted on rolling transaction buffer)

Returns a statistical_score 0–1.
"""

import math
from collections import defaultdict
import numpy as np


# Isolation Forest is fitted lazily once we have enough data per customer
_IF_MIN_SAMPLES = 30

try:
    from sklearn.ensemble import IsolationForest
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False


class StatisticalAnomalyDetector:
    """
    Combines Z-score, IQR, and Isolation Forest signals into
    a single statistical_score 0–1.
    """

    def __init__(self):
        self._buffers:  dict[str, list[float]] = defaultdict(list)
        self._models:   dict[str, object]      = {}
        self._buf_max   = 500

    def _ensure_model(self, cid: str):
        """Fit / refit Isolation Forest for a customer when buffer is large enough."""
        if not _SKLEARN_AVAILABLE:
            return
        buf = self._buffers[cid]
        if len(buf) < _IF_MIN_SAMPLES:
            return
        X = np.array(buf).reshape(-1, 1)
        clf = IsolationForest(
            n_estimators=100,
            contamination=0.05,
            random_state=42,
        )
        clf.fit(X)
        self._models[cid] = clf

    def score(self, transaction: dict, behav_features: dict) -> float:
        """
        Compute statistical anomaly score 0–1 for this transaction.
        """
        cid    = transaction["customer_id"]
        amount = float(transaction["amount"])

        zscore  = behav_features.get("amount_zscore", 0.0)
        amt_pct = behav_features.get("amount_pct",    0.5)
        n_hist  = behav_features.get("profile_n",     0)

        # ── Z-score component ──────────────────────────────────────────────
        z_norm = min(zscore / 10.0, 1.0)   # cap at 10σ → 1.0

        # ── IQR component ─────────────────────────────────────────────────
        buf = self._buffers[cid]
        if len(buf) >= 4:
            arr = np.array(buf)
            q1, q3 = np.percentile(arr, 25), np.percentile(arr, 75)
            iqr = q3 - q1
            if iqr > 0:
                iqr_score = min(max(amount - q3, 0) / (3 * iqr + 1e-9), 1.0)
            else:
                iqr_score = 0.0
        else:
            iqr_score = 0.0

        # ── Isolation Forest component ────────────────────────────────────
        if_score = 0.0
        model = self._models.get(cid)
        if model is not None and _SKLEARN_AVAILABLE:
            raw = model.score_samples([[amount]])[0]
            # score_samples returns negative; more negative = more anomalous
            # Typical range: -0.6 (anomaly) to -0.1 (normal)
            if_score = float(np.clip((-raw - 0.1) / 0.5, 0, 1))

        # ── Composite ─────────────────────────────────────────────────────
        if n_hist < 5:
            # Not enough history — rely on extreme amount alone
            stat_score = min(amount / 100_000, 0.5)
        else:
            w_z  = 0.40
            w_iq = 0.35
            w_if = 0.25 if model is not None else 0.0
            denom = w_z + w_iq + w_if
            stat_score = (w_z * z_norm + w_iq * iqr_score + w_if * if_score) / denom

        # Push amount to buffer
        self._buffers[cid].append(amount)
        if len(self._buffers[cid]) > self._buf_max:
            self._buffers[cid].pop(0)

        # Refit model periodically (every 50 new samples)
        if len(self._buffers[cid]) % 50 == 0:
            self._ensure_model(cid)

        return round(float(stat_score), 4)
