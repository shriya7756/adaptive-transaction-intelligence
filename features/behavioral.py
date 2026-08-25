"""
Behavioral Profile Store — Maintains rolling statistical baselines per customer.

For each customer, tracks:
  - amount distribution (mean, std, percentiles)
  - merchant diversity
  - device usage set
  - category distribution
  - transaction counts per time window
  - geographic center (weighted mean lat/lon)

Uses exponential moving statistics for online updates.
"""

import math
from collections import defaultdict, Counter
from typing import Optional
import numpy as np


class _CustomerBaseline:
    """
    Online statistical baseline for a single customer.
    Uses Welford's online algorithm for running mean/variance.
    """

    def __init__(self):
        # Amount stats (Welford)
        self.n          = 0
        self.mean_amt   = 0.0
        self.M2_amt     = 0.0    # sum of squared deviations

        # Amount percentile buffer (keep last 200)
        self._amt_buffer: list[float] = []
        self._buf_max = 200

        # Entity sets (known entities for this customer)
        self.known_merchants: set[str] = set()
        self.known_devices:   set[str] = set()
        self.known_cities:    set[str] = set()
        self.known_ips:       set[str] = set()

        # Category distribution
        self.category_counts: Counter = Counter()

        # Time-of-day distribution (24 buckets)
        self.hour_counts: list[int] = [0] * 24

        # Geographic centroid
        self.lat_mean  = 0.0
        self.lon_mean  = 0.0
        self.geo_count = 0

        # Payment method
        self.payment_counts: Counter = Counter()

    def update(self, tx: dict):
        amount = float(tx["amount"])
        hour   = int(tx["timestamp"][11:13])   # HH from ISO string

        # Welford update
        self.n += 1
        delta  = amount - self.mean_amt
        self.mean_amt += delta / self.n
        delta2 = amount - self.mean_amt
        self.M2_amt += delta * delta2

        # Percentile buffer
        self._amt_buffer.append(amount)
        if len(self._amt_buffer) > self._buf_max:
            self._amt_buffer.pop(0)

        # Entity sets
        self.known_merchants.add(tx["merchant_id"])
        self.known_devices.add(tx["device_id"])
        self.known_cities.add(tx["city"])
        self.known_ips.add(tx["ip_address"])

        # Distributions
        self.category_counts[tx["category"]] += 1
        self.hour_counts[hour] += 1
        self.payment_counts[tx["payment_method"]] += 1

        # Geographic centroid (incremental)
        lat = tx.get("latitude", 0.0)
        lon = tx.get("longitude", 0.0)
        self.geo_count += 1
        self.lat_mean += (lat - self.lat_mean) / self.geo_count
        self.lon_mean += (lon - self.lon_mean) / self.geo_count

    @property
    def std_amt(self) -> float:
        if self.n < 2:
            return 0.0
        return math.sqrt(self.M2_amt / (self.n - 1))

    def amount_zscore(self, amount: float) -> float:
        if self.std_amt == 0 or self.n < 5:
            return 0.0
        return abs(amount - self.mean_amt) / self.std_amt

    def amount_percentile(self, amount: float) -> float:
        if not self._amt_buffer:
            return 0.5
        buf = sorted(self._amt_buffer)
        below = sum(1 for v in buf if v < amount)
        return below / len(buf)

    def hour_probability(self, hour: int) -> float:
        total = sum(self.hour_counts)
        if total == 0:
            return 1 / 24
        return (self.hour_counts[hour] + 1) / (total + 24)   # Laplace smoothing

    def is_new_merchant(self, merchant_id: str) -> bool:
        return merchant_id not in self.known_merchants

    def is_new_device(self, device_id: str) -> bool:
        return device_id not in self.known_devices

    def is_new_city(self, city: str) -> bool:
        return city not in self.known_cities

    def category_probability(self, category: str) -> float:
        total = sum(self.category_counts.values())
        if total == 0:
            return 0.1
        count = self.category_counts.get(category, 0)
        return (count + 1) / (total + len(self.category_counts) + 1)


class BehavioralProfileStore:
    """
    In-memory store of per-customer behavioral baselines.
    """

    def __init__(self):
        self._profiles: dict[str, _CustomerBaseline] = defaultdict(_CustomerBaseline)

    def get(self, customer_id: str) -> _CustomerBaseline:
        return self._profiles[customer_id]

    def compute(self, transaction: dict) -> dict:
        """
        Extract behavioral deviation features for this transaction.
        Does NOT update the baseline yet (call update() after scoring).
        """
        cid    = transaction["customer_id"]
        prof   = self._profiles[cid]
        amount = float(transaction["amount"])
        hour   = int(transaction["timestamp"][11:13])

        if prof.n == 0:
            # No history yet — return neutral features
            return {
                "profile_n":        0,
                "amount_zscore":    0.0,
                "amount_pct":       0.5,
                "hour_prob":        1 / 24,
                "is_new_merchant":  False,
                "is_new_device":    False,
                "is_new_city":      False,
                "known_merchants":  0,
                "known_devices":    0,
                "category_prob":    0.1,
                "behavioral_score": 0.0,
            }

        zscore   = prof.amount_zscore(amount)
        amt_pct  = prof.amount_percentile(amount)
        hour_p   = prof.hour_probability(hour)
        new_merch = prof.is_new_merchant(transaction["merchant_id"])
        new_dev   = prof.is_new_device(transaction["device_id"])
        new_city  = prof.is_new_city(transaction["city"])
        cat_p    = prof.category_probability(transaction["category"])

        # ── behavioral_score composite 0–1 ────────────────────────────────
        z_norm   = min(zscore / 10, 1.0)           # cap at 10 sigma
        pct_dev  = abs(amt_pct - 0.5) * 2          # 0=median, 1=extreme
        hour_dev = 1.0 - min(hour_p * 24, 1.0)     # 0=common hour, 1=rare hour
        cat_dev  = 1.0 - min(cat_p * 5, 1.0)       # 0=common category, 1=rare
        novelty  = (0.3 * new_merch + 0.4 * new_dev + 0.3 * new_city)

        behavioral_score = (
            0.30 * z_norm   +
            0.15 * pct_dev  +
            0.15 * hour_dev +
            0.10 * cat_dev  +
            0.30 * novelty
        )

        return {
            "profile_n":        prof.n,
            "amount_zscore":    round(zscore, 3),
            "amount_pct":       round(amt_pct, 3),
            "amount_mean":      round(prof.mean_amt, 2),
            "amount_std":       round(prof.std_amt, 2),
            "hour_prob":        round(hour_p, 4),
            "is_new_merchant":  new_merch,
            "is_new_device":    new_dev,
            "is_new_city":      new_city,
            "known_merchants":  len(prof.known_merchants),
            "known_devices":    len(prof.known_devices),
            "category_prob":    round(cat_p, 4),
            "behavioral_score": round(float(behavioral_score), 4),
        }

    def update(self, transaction: dict):
        """Update the customer's baseline with this transaction."""
        cid = transaction["customer_id"]
        self._profiles[cid].update(transaction)
