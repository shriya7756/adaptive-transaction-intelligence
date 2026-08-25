"""
Risk Engine — Weighted composite scorer combining 6 independent signals.

Formula:
  risk = Σ(weight_i × signal_i)

Weights are adaptive: they can be tuned via feedback (post-MVP).
Decision thresholds:
  < 0.30  → SAFE
  0.30–0.60 → REVIEW
  0.60–0.80 → HIGH
  > 0.80  → CRITICAL (auto-block)
"""

from typing import Optional


# Default weights — sum to 1.0
DEFAULT_WEIGHTS = {
    "statistical":  0.25,
    "behavioral":   0.20,
    "velocity":     0.18,
    "geographic":   0.15,
    "temporal":     0.10,
    "relationship": 0.12,
}

THRESHOLDS = {
    "SAFE":     0.30,
    "REVIEW":   0.60,
    "HIGH":     0.80,
    # > 0.80 → CRITICAL
}


class RiskEngine:

    def __init__(self, weights: Optional[dict] = None):
        self._weights = weights or DEFAULT_WEIGHTS.copy()
        self._validate_weights()

    def _validate_weights(self):
        total = sum(self._weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")

    def score(self, signals: dict[str, float], transaction: dict) -> dict:
        """
        Compute composite risk score.

        signals: dict of {signal_name: 0–1 float}
        Returns: {score: 0–1, level: str, decision: str, breakdown: dict}
        """
        composite = 0.0
        breakdown = {}
        for name, weight in self._weights.items():
            sig_val = signals.get(name, 0.0)
            contribution = weight * sig_val
            composite += contribution
            breakdown[name] = {
                "signal":       round(sig_val, 4),
                "weight":       weight,
                "contribution": round(contribution, 4),
            }

        composite = min(max(composite, 0.0), 1.0)

        # ── Level & Decision ───────────────────────────────────────────────
        if composite < THRESHOLDS["SAFE"]:
            level    = "LOW"
            decision = "SAFE"
        elif composite < THRESHOLDS["REVIEW"]:
            level    = "MEDIUM"
            decision = "REVIEW"
        elif composite < THRESHOLDS["HIGH"]:
            level    = "HIGH"
            decision = "REVIEW"
        else:
            level    = "CRITICAL"
            decision = "BLOCK"

        return {
            "score":     round(composite, 4),
            "level":     level,
            "decision":  decision,
            "breakdown": breakdown,
        }

    def update_weights(self, new_weights: dict):
        """Adaptive weight update (future: gradient-based tuning)."""
        self._weights = new_weights
        self._validate_weights()

    @property
    def weights(self) -> dict:
        return self._weights.copy()
