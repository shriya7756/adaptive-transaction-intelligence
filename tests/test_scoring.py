"""Tests for the Risk Engine and Explanation Engine."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scoring.risk_engine  import RiskEngine, DEFAULT_WEIGHTS
from scoring.explanation  import ExplanationEngine


SAFE_SIGNALS = {
    "statistical":  0.05,
    "behavioral":   0.03,
    "velocity":     0.02,
    "geographic":   0.00,
    "temporal":     0.08,
    "relationship": 0.01,
}

HIGH_SIGNALS = {
    "statistical":  0.90,
    "behavioral":   0.85,
    "velocity":     0.80,
    "geographic":   0.70,
    "temporal":     0.75,
    "relationship": 0.60,
}

SAMPLE_TX = {
    "transaction_id": "test-score-001",
    "customer_id":    "CUST_test0000",
    "merchant_id":    "MERCH_test000",
    "device_id":      "DEV_test00000",
    "amount":         75000.0,
    "city":           "Mumbai",
    "latitude":       19.076,
    "longitude":      72.8777,
    "timestamp":      "2025-01-15T02:17:00",
    "category":       "jewelry",
    "payment_method": "Credit Card",
}


def test_risk_engine_safe():
    engine = RiskEngine()
    result = engine.score(SAFE_SIGNALS, SAMPLE_TX)
    assert result["level"]    == "LOW"
    assert result["decision"] == "SAFE"
    assert result["score"] < 0.30


def test_risk_engine_critical():
    engine = RiskEngine()
    result = engine.score(HIGH_SIGNALS, SAMPLE_TX)
    assert result["level"] in ("HIGH", "CRITICAL")
    assert result["decision"] in ("REVIEW", "BLOCK")
    assert result["score"] > 0.60


def test_risk_engine_breakdown_sums():
    engine = RiskEngine()
    result = engine.score(SAFE_SIGNALS, SAMPLE_TX)
    total_contribution = sum(v["contribution"] for v in result["breakdown"].values())
    assert abs(total_contribution - result["score"]) < 0.001


def test_risk_engine_weights_sum_to_one():
    engine = RiskEngine()
    assert abs(sum(engine.weights.values()) - 1.0) < 0.01


def test_explanation_engine_high_risk():
    explainer = ExplanationEngine()
    behav = {
        "profile_n":      50,
        "amount_zscore":  8.4,
        "amount_mean":    3000.0,
        "amount_std":     800.0,
        "is_new_device":  True,
        "is_new_merchant": True,
        "is_new_city":    False,
        "known_devices":  2,
        "known_merchants": 8,
    }
    vel  = {"tx_count_5m": 9, "tx_count_1h": 15, "tx_amount_5m": 150000, "inter_tx_seconds": 22}
    geo  = {"distance_from_home_km": 1400, "is_international": False, "city": "Mumbai", "geo_score": 0.55}
    temp = {"hour_of_day": 2, "is_odd_hours": True, "temporal_score": 0.85}

    reasons = explainer.explain(SAMPLE_TX, HIGH_SIGNALS, behav, vel, geo, temp)
    assert len(reasons) > 0
    # Highest severity should come first
    severities = [r["severity"] for r in reasons]
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    assert all(order[severities[i]] <= order[severities[i+1]] for i in range(len(severities)-1))
