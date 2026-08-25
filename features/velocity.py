"""
Velocity Features — Rolling-window transaction frequency signals.

Windows:  5m | 1h | 24h | 7d | 30d
Signals:
  - tx count in each window
  - cumulative amount in each window
  - unique merchant count
  - unique device count
  - inter-transaction time (seconds since last tx)
  - velocity_score: composite 0-1
"""

import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Optional
import numpy as np


WINDOWS = {
    "5m":  5   * 60,
    "1h":  60  * 60,
    "24h": 24  * 60 * 60,
    "7d":  7   * 24 * 60 * 60,
    "30d": 30  * 24 * 60 * 60,
}

# High-risk thresholds (per window)
ALERT_TX_COUNTS = {
    "5m":  6,
    "1h":  20,
    "24h": 60,
    "7d":  200,
    "30d": 500,
}
ALERT_AMOUNTS = {
    "5m":  50_000,
    "1h":  100_000,
    "24h": 500_000,
    "7d":  2_000_000,
    "30d": 5_000_000,
}


class _CustomerWindow:
    """Sliding window buffer for a single customer."""
    def __init__(self):
        # Each entry: (epoch_float, amount, merchant_id, device_id)
        self.events: deque = deque()

    def push(self, amount: float, merchant: str, device: str):
        # Record wall-clock time at ingestion to avoid UTC vs local tz mismatch
        self.events.append((time.time(), amount, merchant, device))

    def prune(self, horizon: float):
        """Remove events older than horizon seconds."""
        cutoff = time.time() - horizon
        while self.events and self.events[0][0] < cutoff:
            self.events.popleft()

    def stats(self, window_seconds: float) -> dict:
        cutoff = time.time() - window_seconds
        relevant = [(ts, amt, m, d) for ts, amt, m, d in self.events if ts >= cutoff]
        if not relevant:
            return {"count": 0, "amount": 0.0, "merchants": 0, "devices": 0}
        amounts   = [r[1] for r in relevant]
        merchants = len(set(r[2] for r in relevant))
        devices   = len(set(r[3] for r in relevant))
        return {
            "count":     len(relevant),
            "amount":    sum(amounts),
            "merchants": merchants,
            "devices":   devices,
        }


class VelocityFeatures:
    """
    Maintains per-customer sliding window buffers and computes velocity features.
    """

    def __init__(self):
        self._windows: dict[str, _CustomerWindow] = defaultdict(_CustomerWindow)
        self._last_tx_time: dict[str, float] = {}

    def compute(self, transaction: dict) -> dict:
        cid    = transaction["customer_id"]
        amount = float(transaction["amount"])
        merch  = transaction["merchant_id"]
        device = transaction["device_id"]

        win = self._windows[cid]
        # Prune oldest window to keep memory bounded
        win.prune(WINDOWS["30d"])

        features: dict = {}
        anomaly_flags: list[str] = []

        for wname, wsec in WINDOWS.items():
            s = win.stats(wsec)
            features[f"tx_count_{wname}"]   = s["count"]
            features[f"tx_amount_{wname}"]  = s["amount"]
            features[f"merchants_{wname}"]  = s["merchants"]
            features[f"devices_{wname}"]    = s["devices"]

            if s["count"] >= ALERT_TX_COUNTS[wname]:
                anomaly_flags.append(f"high_frequency_{wname}")
            if s["amount"] >= ALERT_AMOUNTS[wname]:
                anomaly_flags.append(f"high_amount_{wname}")

        # Inter-transaction time
        last_ts = self._last_tx_time.get(cid)
        now = time.time()
        if last_ts:
            inter_tx_seconds = now - last_ts
            features["inter_tx_seconds"] = inter_tx_seconds
        else:
            features["inter_tx_seconds"] = None

        features["anomaly_flags"] = anomaly_flags

        # ── velocity_score: composite 0–1 ──────────────────────────────────
        # Weighted from the 5m and 1h windows (fastest signals matter most)
        count_5m   = features["tx_count_5m"]
        count_1h   = features["tx_count_1h"]
        amount_5m  = features["tx_amount_5m"]
        devices_5m = features["devices_5m"]

        # Normalise against thresholds
        c5  = min(count_5m  / ALERT_TX_COUNTS["5m"],  1.0)
        c1h = min(count_1h  / ALERT_TX_COUNTS["1h"],  1.0)
        a5  = min(amount_5m / ALERT_AMOUNTS["5m"],    1.0)
        d5  = min(devices_5m / 3, 1.0)   # >3 devices in 5m is suspicious

        velocity_score = 0.35 * c5 + 0.25 * c1h + 0.25 * a5 + 0.15 * d5
        features["velocity_score"] = round(float(velocity_score), 4)

        return features

    def update(self, transaction: dict):
        """Call AFTER compute to push this transaction into the window."""
        cid    = transaction["customer_id"]
        amount = float(transaction["amount"])
        merch  = transaction["merchant_id"]
        device = transaction["device_id"]

        self._windows[cid].push(amount, merch, device)
        self._last_tx_time[cid] = time.time()
