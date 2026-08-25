"""
Temporal Features — Time-of-day and inter-transaction timing anomaly signals.

Signals:
  - is_odd_hours: transaction between 1–5 AM
  - hour_of_day, day_of_week
  - temporal_score: 0–1 composite
"""

from datetime import datetime
import math


# Hours considered "off-hours" (higher risk)
OFF_HOURS = set(range(1, 5))    # 1 AM – 4 AM inclusive
MODERATE_OFF_HOURS = set(range(23, 24)) | set(range(0, 1))  # midnight


class TemporalFeatures:
    """Stateless temporal feature extractor."""

    def compute(self, transaction: dict) -> dict:
        ts          = datetime.fromisoformat(transaction["timestamp"])
        hour        = ts.hour
        dow         = ts.weekday()   # 0=Monday, 6=Sunday
        is_weekend  = dow >= 5

        is_odd    = hour in OFF_HOURS
        is_mod    = hour in MODERATE_OFF_HOURS

        # Temporal risk: peak at 2–3 AM, low at 9–6 PM
        # Simple sinusoidal distance from "safe zone" centre (13:00)
        safe_centre = 13.0
        hour_dist   = min(abs(hour - safe_centre), 24 - abs(hour - safe_centre))
        # Normalise: max dist is 13 hours → score 0–1
        temporal_base = hour_dist / 13.0

        # Boost for the deep-night window
        if is_odd:
            temporal_base = min(temporal_base * 1.4, 1.0)
        elif is_mod:
            temporal_base = min(temporal_base * 1.1, 1.0)

        # Weekend effect (slight lift)
        if is_weekend:
            temporal_base = min(temporal_base * 1.05, 1.0)

        return {
            "hour_of_day":      hour,
            "day_of_week":      dow,
            "is_weekend":       is_weekend,
            "is_odd_hours":     is_odd,
            "is_moderate_off":  is_mod,
            "temporal_score":   round(float(temporal_base), 4),
        }
