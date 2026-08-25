"""Tests for velocity, behavioral, temporal, and geographic feature extractors."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from features.velocity   import VelocityFeatures
from features.behavioral import BehavioralProfileStore
from features.temporal   import TemporalFeatures
from features.geographic import GeographicFeatures


SAMPLE_TX = {
    "transaction_id": "test-001",
    "customer_id":    "CUST_abc12345",
    "merchant_id":    "MERCH_xyz9876",
    "device_id":      "DEV_111aaaaa",
    "ip_address":     "10.0.1.50",
    "amount":         2500.0,
    "currency":       "INR",
    "category":       "grocery",
    "payment_method": "UPI",
    "city":           "Hyderabad",
    "latitude":       17.385,
    "longitude":      78.4867,
    "timestamp":      "2025-01-15T14:30:00",
    "is_fraud":       False,
    "anomaly_type":   "normal",
}


def test_velocity_cold_start():
    vel = VelocityFeatures()
    f = vel.compute(SAMPLE_TX)
    assert "velocity_score" in f
    assert 0.0 <= f["velocity_score"] <= 1.0
    assert f["tx_count_5m"] == 0   # nothing in window yet


def test_velocity_accumulates():
    vel = VelocityFeatures()
    # Must use current timestamp so the sliding 5-minute window includes these events
    now_tx = {**SAMPLE_TX, "timestamp": datetime.utcnow().isoformat()}
    for _ in range(8):
        vel.compute(now_tx)
        vel.update(now_tx)
    f = vel.compute(now_tx)
    assert f["tx_count_5m"] > 0
    assert f["velocity_score"] > 0


def test_behavioral_cold_start():
    store = BehavioralProfileStore()
    f = store.compute(SAMPLE_TX)
    assert f["profile_n"] == 0
    assert f["behavioral_score"] == 0.0


def test_behavioral_new_device_flag():
    store = BehavioralProfileStore()
    # Seed some history
    for _ in range(10):
        store.update(SAMPLE_TX)
    # Now transact from a different device
    tx2 = {**SAMPLE_TX, "device_id": "DEV_brandnew"}
    f = store.compute(tx2)
    assert f["is_new_device"] is True


def test_temporal_odd_hours():
    temp = TemporalFeatures()
    tx_night = {**SAMPLE_TX, "timestamp": "2025-01-15T02:30:00"}
    f = temp.compute(tx_night)
    assert f["is_odd_hours"] is True
    assert f["temporal_score"] > 0.5


def test_temporal_daytime():
    temp = TemporalFeatures()
    tx_day = {**SAMPLE_TX, "timestamp": "2025-01-15T13:00:00"}
    f = temp.compute(tx_day)
    assert f["is_odd_hours"] is False
    assert f["temporal_score"] < 0.3


def test_geographic_same_city():
    geo = GeographicFeatures()
    f = geo.compute(SAMPLE_TX)
    assert f["distance_from_home_km"] == 0.0
    assert f["geo_score"] == 0.0


def test_geographic_international():
    geo = GeographicFeatures()
    geo.compute(SAMPLE_TX)   # establish centroid
    tx_intl = {**SAMPLE_TX, "city": "Dubai", "latitude": 25.2048, "longitude": 55.2708}
    f = geo.compute(tx_intl)
    assert f["is_international"] is True
    assert f["geo_score"] >= 0.5
