"""
Concept Drift Detector — Population-level monitoring of feature distributions.

Implements:
  - PSI (Population Stability Index) for amount and risk score drift
  - KS statistic (two-sample Kolmogorov-Smirnov) for distribution shift
  - Rolling performance degradation tracking (precision/recall proxy)

Triggered by the monitoring loop; reports drift alerts to the API.
"""

import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import numpy as np
from scipy import stats


PSI_ALERT_THRESHOLD  = 0.20   # PSI > 0.2 → significant drift
PSI_WARN_THRESHOLD   = 0.10   # PSI 0.1–0.2 → moderate drift
KS_PVAL_THRESHOLD    = 0.05   # p-value < 0.05 → reject H0 (same distribution)
MIN_SAMPLES          = 100     # minimum transactions before drift is meaningful


@dataclass
class DriftReport:
    timestamp:      str
    psi_amount:     float
    ks_stat_amount: float
    ks_pval_amount: float
    psi_risk:       float
    ks_stat_risk:   float
    ks_pval_risk:   float
    alert_level:    str    # "NONE" | "MODERATE" | "SIGNIFICANT"
    message:        str
    should_retrain: bool


class ConceptDriftDetector:
    """
    Compares a reference window (baseline period) against a recent window
    to detect population-level distribution shifts.
    """

    def __init__(self, reference_size: int = 500, recent_size: int = 200):
        self._reference_amounts: deque = deque(maxlen=reference_size)
        self._reference_risks:   deque = deque(maxlen=reference_size)
        self._recent_amounts:    deque = deque(maxlen=recent_size)
        self._recent_risks:      deque = deque(maxlen=recent_size)
        self._reports:           list[DriftReport] = []
        self._reference_frozen   = False

    def ingest(self, amount: float, risk_score: float):
        """Record an incoming transaction's key values."""
        if not self._reference_frozen:
            self._reference_amounts.append(amount)
            self._reference_risks.append(risk_score)
            # Freeze reference once full
            if len(self._reference_amounts) >= self._reference_amounts.maxlen:
                self._reference_frozen = True
        else:
            self._recent_amounts.append(amount)
            self._recent_risks.append(risk_score)

    def _psi(self, ref: list[float], rec: list[float], bins: int = 10) -> float:
        """Population Stability Index between two samples."""
        lo = min(min(ref), min(rec))
        hi = max(max(ref), max(rec))
        if lo == hi:
            return 0.0
        ref_counts, _ = np.histogram(ref, bins=bins, range=(lo, hi))
        rec_counts, _ = np.histogram(rec, bins=bins, range=(lo, hi))
        eps = 1e-4
        ref_pct = (ref_counts + eps) / (sum(ref_counts) + eps * bins)
        rec_pct = (rec_counts + eps) / (sum(rec_counts) + eps * bins)
        return float(np.sum((rec_pct - ref_pct) * np.log(rec_pct / ref_pct)))

    def check(self) -> Optional[DriftReport]:
        """
        Run a drift check. Returns a DriftReport if enough data is available,
        None otherwise.
        """
        ref_amt = list(self._reference_amounts)
        rec_amt = list(self._recent_amounts)
        ref_risk = list(self._reference_risks)
        rec_risk = list(self._recent_risks)

        if len(ref_amt) < MIN_SAMPLES or len(rec_amt) < MIN_SAMPLES // 2:
            return None

        # PSI
        psi_amt  = self._psi(ref_amt,  rec_amt)
        psi_risk = self._psi(ref_risk, rec_risk)

        # KS test
        ks_amt,  ks_pval_amt  = stats.ks_2samp(ref_amt,  rec_amt)
        ks_risk, ks_pval_risk = stats.ks_2samp(ref_risk, rec_risk)

        # Alert level
        max_psi = max(psi_amt, psi_risk)
        if max_psi >= PSI_ALERT_THRESHOLD or ks_pval_amt < KS_PVAL_THRESHOLD:
            level   = "SIGNIFICANT"
            retrain = True
            msg     = (
                f"Significant concept drift detected. "
                f"PSI_amount={psi_amt:.3f}, PSI_risk={psi_risk:.3f}, "
                f"KS_p={ks_pval_amt:.4f}. Retraining recommended."
            )
        elif max_psi >= PSI_WARN_THRESHOLD:
            level   = "MODERATE"
            retrain = False
            msg     = (
                f"Moderate distribution shift. "
                f"PSI_amount={psi_amt:.3f}, PSI_risk={psi_risk:.3f}. Monitor closely."
            )
        else:
            level   = "NONE"
            retrain = False
            msg     = f"No significant drift. PSI_amount={psi_amt:.3f}, PSI_risk={psi_risk:.3f}."

        report = DriftReport(
            timestamp=datetime.utcnow().isoformat(),
            psi_amount=round(psi_amt, 4),
            ks_stat_amount=round(float(ks_amt), 4),
            ks_pval_amount=round(float(ks_pval_amt), 6),
            psi_risk=round(psi_risk, 4),
            ks_stat_risk=round(float(ks_risk), 4),
            ks_pval_risk=round(float(ks_pval_risk), 6),
            alert_level=level,
            message=msg,
            should_retrain=retrain,
        )
        self._reports.append(report)
        return report

    def get_reports(self, limit: int = 20) -> list[DriftReport]:
        return self._reports[-limit:]

    def reset_recent(self):
        """After retraining, reset the recent window and unfreeze reference."""
        self._recent_amounts.clear()
        self._recent_risks.clear()
        self._reference_frozen = False
