"""
Explanation Engine — Generates human-readable risk reasons.

Combines:
  - Rule-based reasons from each signal (always available)
  - SHAP model-level explanations (when XGBoost model is loaded)

Output format:
  [
    {"signal": "velocity", "reason": "9 transactions within 5 minutes", "severity": "HIGH"},
    {"signal": "behavioral", "reason": "Amount 8.4σ above baseline", "severity": "HIGH"},
    ...
  ]
"""

from typing import Optional


SEVERITY_LEVELS = {
    (0.00, 0.30): "LOW",
    (0.30, 0.60): "MEDIUM",
    (0.60, 0.80): "HIGH",
    (0.80, 1.01): "CRITICAL",
}


def _severity(score: float) -> str:
    for (lo, hi), level in SEVERITY_LEVELS.items():
        if lo <= score < hi:
            return level
    return "LOW"


class ExplanationEngine:

    def explain(
        self,
        transaction: dict,
        signals: dict[str, float],
        behav:   dict,
        vel:     dict,
        geo:     dict,
        temp:    dict,
    ) -> list[dict]:
        """
        Build the ordered list of risk reasons, highest severity first.
        """
        reasons: list[dict] = []

        # ── Statistical / Behavioral ───────────────────────────────────────
        if signals.get("statistical", 0) > 0.2 or signals.get("behavioral", 0) > 0.2:
            zscore    = behav.get("amount_zscore", 0.0)
            mean_amt  = behav.get("amount_mean",   0.0)
            std_amt   = behav.get("amount_std",     0.0)
            amt       = float(transaction.get("amount", 0))
            n_history = behav.get("profile_n", 0)
            sev_score = max(signals.get("statistical", 0), signals.get("behavioral", 0))

            if zscore >= 2.0 and n_history >= 5:
                reasons.append({
                    "signal":   "statistical",
                    "reason":   f"Amount ₹{amt:,.0f} is {zscore:.1f}σ above baseline "
                                f"(mean ₹{mean_amt:,.0f}, std ₹{std_amt:,.0f})",
                    "severity": _severity(sev_score),
                    "score":    round(sev_score, 3),
                })
            elif n_history < 5:
                reasons.append({
                    "signal":   "statistical",
                    "reason":   "Insufficient transaction history — first 5 transactions",
                    "severity": "LOW",
                    "score":    0.1,
                })

        # ── New entity signals ─────────────────────────────────────────────
        if behav.get("is_new_device"):
            reasons.append({
                "signal":   "behavioral",
                "reason":   f"Transaction from unrecognised device (customer has "
                            f"{behav.get('known_devices', 0)} known device(s))",
                "severity": _severity(0.65),
                "score":    0.65,
            })
        if behav.get("is_new_merchant"):
            reasons.append({
                "signal":   "behavioral",
                "reason":   "New merchant — not in customer's historical merchant set",
                "severity": _severity(0.35),
                "score":    0.35,
            })
        if behav.get("is_new_city"):
            reasons.append({
                "signal":   "behavioral",
                "reason":   "Transaction in a new city not seen in customer history",
                "severity": _severity(0.45),
                "score":    0.45,
            })

        # ── Velocity ──────────────────────────────────────────────────────
        vel_score = signals.get("velocity", 0.0)
        if vel_score > 0.1:
            count_5m  = vel.get("tx_count_5m",  0)
            count_1h  = vel.get("tx_count_1h",  0)
            amt_5m    = vel.get("tx_amount_5m", 0)
            inter_tx  = vel.get("inter_tx_seconds")

            if count_5m >= 4:
                reasons.append({
                    "signal":   "velocity",
                    "reason":   f"{count_5m} transactions within the last 5 minutes "
                                f"(₹{amt_5m:,.0f} total)",
                    "severity": _severity(vel_score),
                    "score":    round(vel_score, 3),
                })
            elif count_1h >= 12:
                reasons.append({
                    "signal":   "velocity",
                    "reason":   f"{count_1h} transactions within the last hour",
                    "severity": _severity(vel_score),
                    "score":    round(vel_score, 3),
                })
            elif inter_tx is not None and inter_tx < 30:
                reasons.append({
                    "signal":   "velocity",
                    "reason":   f"Only {inter_tx:.0f}s since previous transaction",
                    "severity": _severity(vel_score),
                    "score":    round(vel_score, 3),
                })

        # ── Geographic ────────────────────────────────────────────────────
        geo_score = signals.get("geographic", 0.0)
        if geo_score > 0.1:
            dist = geo.get("distance_from_home_km", 0)
            city = geo.get("city", "")
            intl = geo.get("is_international", False)
            if intl:
                reasons.append({
                    "signal":   "geographic",
                    "reason":   f"International transaction in {city} "
                                f"({dist:,.0f} km from home region)",
                    "severity": _severity(geo_score),
                    "score":    round(geo_score, 3),
                })
            elif dist > 100:
                reasons.append({
                    "signal":   "geographic",
                    "reason":   f"Transaction {dist:,.0f} km from customer's home city",
                    "severity": _severity(geo_score),
                    "score":    round(geo_score, 3),
                })

        # ── Temporal ──────────────────────────────────────────────────────
        temp_score = signals.get("temporal", 0.0)
        if temp_score > 0.3:
            hour = temp.get("hour_of_day", 0)
            reasons.append({
                "signal":   "temporal",
                "reason":   f"Transaction at {hour:02d}:00 — outside normal activity window",
                "severity": _severity(temp_score),
                "score":    round(temp_score, 3),
            })

        # ── Relationship ─────────────────────────────────────────────────
        rel_score = signals.get("relationship", 0.0)
        if rel_score > 0.2:
            reasons.append({
                "signal":   "relationship",
                "reason":   "Device or IP linked to multiple distinct accounts",
                "severity": _severity(rel_score),
                "score":    round(rel_score, 3),
            })

        # Sort by severity (CRITICAL → HIGH → MEDIUM → LOW)
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        reasons.sort(key=lambda r: (order.get(r["severity"], 4), -r.get("score", 0)))

        return reasons
