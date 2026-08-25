"""
Transaction Generator — India-flavored synthetic financial transactions.
Produces realistic distributions for amounts, merchants, locations, devices,
and timing patterns including anomalous/fraudulent bursts.
"""

import random
import uuid
import time
from datetime import datetime, timedelta
from typing import Optional
import numpy as np

# ── Geography ──────────────────────────────────────────────────────────────────
CITIES = [
    {"name": "Hyderabad",  "lat": 17.3850, "lon": 78.4867},
    {"name": "Bangalore",  "lat": 12.9716, "lon": 77.5946},
    {"name": "Mumbai",     "lat": 19.0760, "lon": 72.8777},
    {"name": "Delhi",      "lat": 28.7041, "lon": 77.1025},
    {"name": "Chennai",    "lat": 13.0827, "lon": 80.2707},
    {"name": "Pune",       "lat": 18.5204, "lon": 73.8567},
    {"name": "Kolkata",    "lat": 22.5726, "lon": 88.3639},
    {"name": "Ahmedabad",  "lat": 23.0225, "lon": 72.5714},
    {"name": "Jaipur",     "lat": 26.9124, "lon": 75.7873},
    {"name": "Surat",      "lat": 21.1702, "lon": 72.8311},
    {"name": "Dubai",      "lat": 25.2048, "lon": 55.2708},   # international
    {"name": "Singapore",  "lat":  1.3521, "lon": 103.8198},  # international
    {"name": "London",     "lat": 51.5074, "lon": -0.1278},   # international
]

MERCHANT_CATEGORIES = {
    "grocery":      (200,  3_000,   0.22),
    "food_dining":  (150,  2_500,   0.18),
    "fuel":         (500,  4_000,   0.10),
    "electronics":  (2000, 80_000,  0.06),
    "apparel":      (400,  15_000,  0.08),
    "travel":       (3000, 120_000, 0.05),
    "healthcare":   (300,  20_000,  0.07),
    "utilities":    (100,  5_000,   0.05),
    "entertainment":(200,  5_000,   0.06),
    "atm_cash":     (500,  20_000,  0.08),
    "jewelry":      (5000, 200_000, 0.02),
    "subscription": (99,   2_000,   0.03),
}

PAYMENT_METHODS = ["UPI", "Credit Card", "Debit Card", "Wallet", "NEFT"]

# Pre-generate a pool of synthetic entities
NUM_CUSTOMERS  = 200
NUM_MERCHANTS  = 120
NUM_DEVICES    = 350   # more devices than customers — shared devices are anomaly signals
NUM_IPS        = 500

rng = np.random.default_rng(42)


def _pool(prefix: str, n: int) -> list[str]:
    return [f"{prefix}_{str(uuid.UUID(int=i)).split('-')[0]}" for i in range(n)]


CUSTOMER_IDS  = _pool("CUST",  NUM_CUSTOMERS)
MERCHANT_IDS  = _pool("MERCH", NUM_MERCHANTS)
DEVICE_IDS    = _pool("DEV",   NUM_DEVICES)
IP_POOL       = [f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}" for _ in range(NUM_IPS)]

# Each customer has a "home city" and preferred device set
CUSTOMER_PROFILE: dict[str, dict] = {}
for cid in CUSTOMER_IDS:
    home_city = random.choice(CITIES[:8])          # domestic home
    devices   = random.sample(DEVICE_IDS, random.randint(1, 3))
    merchants = random.sample(MERCHANT_IDS, random.randint(5, 20))
    categories = random.choices(
        list(MERCHANT_CATEGORIES.keys()),
        weights=[v[2] for v in MERCHANT_CATEGORIES.values()],
        k=random.randint(3, 7),
    )
    CUSTOMER_PROFILE[cid] = {
        "home_city":         home_city,
        "preferred_devices": devices,
        "preferred_merchants": merchants,
        "preferred_categories": list(set(categories)),
        "avg_amount":        rng.uniform(500, 8_000),
        "std_amount":        rng.uniform(200, 2_000),
        "normal_hour_start": random.randint(7, 10),
        "normal_hour_end":   random.randint(20, 23),
        "avg_daily_tx":      rng.uniform(2, 8),
    }


def generate_transaction(
    customer_id: Optional[str] = None,
    anomaly_type: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> dict:
    """
    Generate one synthetic transaction.

    anomaly_type options:
        'large_amount'   — abnormally high amount
        'new_device'     — device not in customer profile
        'foreign'        — location far from home city
        'odd_hours'      — transaction at 1–4 AM
        'velocity_burst' — (caller generates many in quick succession)
        'coordinated'    — multiple customers, same device
        None             — normal transaction
    """
    if customer_id is None:
        customer_id = random.choice(CUSTOMER_IDS)

    profile = CUSTOMER_PROFILE[customer_id]
    if timestamp is None:
        timestamp = datetime.utcnow()

    # ── category & amount ──────────────────────────────────────────────────
    category = random.choice(profile["preferred_categories"]) if anomaly_type not in ("large_amount",) else "jewelry"
    cat_cfg  = MERCHANT_CATEGORIES[category]

    if anomaly_type == "large_amount":
        amount = round(rng.uniform(cat_cfg[0] * 5, cat_cfg[1] * 3), 2)
    else:
        mean = profile["avg_amount"]
        std  = profile["std_amount"]
        raw  = abs(rng.normal(mean, std))
        amount = round(float(np.clip(raw, cat_cfg[0], cat_cfg[1])), 2)

    # ── merchant ────────────────────────────────────────────────────────────
    if anomaly_type == "foreign" or random.random() < 0.05:
        merchant_id = random.choice(MERCHANT_IDS)
    else:
        merchant_id = random.choice(profile["preferred_merchants"])

    # ── device ──────────────────────────────────────────────────────────────
    if anomaly_type in ("new_device", "coordinated"):
        # pick a device outside the customer's preferred set
        foreign_devs = [d for d in DEVICE_IDS if d not in profile["preferred_devices"]]
        device_id = random.choice(foreign_devs)
    else:
        device_id = random.choice(profile["preferred_devices"])

    # ── location ────────────────────────────────────────────────────────────
    if anomaly_type == "foreign":
        location = random.choice(CITIES[8:])   # international
    elif random.random() < 0.03:
        location = random.choice(CITIES)
    else:
        location = profile["home_city"]

    # ── time ────────────────────────────────────────────────────────────────
    if anomaly_type == "odd_hours":
        hour = random.randint(1, 4)
    else:
        hour = random.randint(profile["normal_hour_start"], profile["normal_hour_end"])
    # replace timestamp hour (keep date)
    ts = timestamp.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))

    # ── payment method ────────────────────────────────────────────────────
    payment_method = random.choices(
        PAYMENT_METHODS,
        weights=[0.35, 0.30, 0.20, 0.10, 0.05],
    )[0]

    tx_id = str(uuid.uuid4())

    return {
        "transaction_id":  tx_id,
        "customer_id":     customer_id,
        "merchant_id":     merchant_id,
        "device_id":       device_id,
        "ip_address":      random.choice(IP_POOL),
        "amount":          amount,
        "currency":        "INR",
        "category":        category,
        "payment_method":  payment_method,
        "city":            location["name"],
        "latitude":        location["lat"],
        "longitude":       location["lon"],
        "timestamp":       ts.isoformat(),
        "is_fraud":        anomaly_type is not None,   # label for training
        "anomaly_type":    anomaly_type or "normal",
    }


def generate_fraud_burst(n: int = 10, coordinated_device: Optional[str] = None) -> list[dict]:
    """
    Generate a coordinated fraud burst: multiple customers using the same device
    transacting with overlapping merchants in a short time window.
    """
    device = coordinated_device or random.choice(DEVICE_IDS)
    customers = random.sample(CUSTOMER_IDS, min(n, len(CUSTOMER_IDS)))
    now = datetime.utcnow()
    txns = []
    for i, cid in enumerate(customers):
        ts = now + timedelta(seconds=i * random.randint(10, 45))
        tx = generate_transaction(customer_id=cid, anomaly_type="coordinated", timestamp=ts)
        tx["device_id"] = device   # force same device — the coordination signal
        txns.append(tx)
    return txns


def stream_transactions(delay_seconds: float = 0.5, fraud_rate: float = 0.05):
    """
    Infinite generator yielding synthetic transactions with realistic timing.
    Inject anomalies at fraud_rate probability.
    """
    anomaly_types = ["large_amount", "new_device", "foreign", "odd_hours", "velocity_burst"]
    while True:
        if random.random() < fraud_rate:
            atype = random.choice(anomaly_types)
            if atype == "velocity_burst":
                for tx in generate_fraud_burst(n=random.randint(6, 12)):
                    yield tx
                    time.sleep(delay_seconds * 0.1)
                continue
            else:
                tx = generate_transaction(anomaly_type=atype)
        else:
            tx = generate_transaction()
        yield tx
        time.sleep(delay_seconds)
