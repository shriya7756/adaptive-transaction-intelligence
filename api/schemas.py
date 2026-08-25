"""
Pydantic schemas for FastAPI request / response models.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ── Inbound ────────────────────────────────────────────────────────────────────

class TransactionIn(BaseModel):
    """Manual transaction submission (e.g., from the what-if simulator)."""
    customer_id:    str
    merchant_id:    str
    device_id:      str
    ip_address:     str   = "10.0.0.1"
    amount:         float = Field(..., gt=0)
    currency:       str   = "INR"
    category:       str   = "grocery"
    payment_method: str   = "UPI"
    city:           str   = "Hyderabad"
    latitude:       float = 17.3850
    longitude:      float = 78.4867
    timestamp:      Optional[str] = None   # ISO 8601; defaults to now


class SimulateIn(BaseModel):
    """What-if simulator payload — subset of transaction fields."""
    customer_id:    Optional[str]   = None
    amount:         float           = Field(2000, gt=0)
    city:           str             = "Hyderabad"
    latitude:       float           = 17.3850
    longitude:      float           = 78.4867
    device_id:      Optional[str]   = None    # None → use customer's known device
    merchant_id:    Optional[str]   = None
    currency:       str             = "INR"
    ip_address:     str             = "10.0.0.1"
    category:       str             = "grocery"
    payment_method: str             = "UPI"
    hour_override:  Optional[int]   = None    # 0–23; overrides hour in timestamp


class FeedbackIn(BaseModel):
    transaction_id: str
    is_fraud:       bool
    analyst_note:   Optional[str] = None


# ── Outbound ───────────────────────────────────────────────────────────────────

class SignalBreakdown(BaseModel):
    statistical:  float
    behavioral:   float
    velocity:     float
    geographic:   float
    temporal:     float
    relationship: float


class RiskReason(BaseModel):
    signal:   str
    reason:   str
    severity: str
    score:    float


class ScoredTransaction(BaseModel):
    transaction_id: str
    customer_id:    str
    merchant_id:    str
    device_id:      str
    amount:         float
    currency:       str
    category:       str
    city:           str
    timestamp:      str
    risk_score:     float
    risk_level:     str
    decision:       str
    signals:        dict
    reasons:        list[RiskReason]
    processed_at:   str
