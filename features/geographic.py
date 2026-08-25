"""
Geographic Features — Distance-based anomaly signals.

Signals:
  - distance_from_home_km: haversine distance from customer's home city
  - is_international: transaction in a non-domestic city
  - geo_score: 0–1 composite
"""

import math
from collections import defaultdict
from features.behavioral import BehavioralProfileStore


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine great-circle distance in kilometres."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi  = math.radians(lat2 - lat1)
    dlam  = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


INTERNATIONAL_CITIES = {"Dubai", "Singapore", "London", "New York", "Tokyo"}

# Distance thresholds (km)
DOMESTIC_SAFE_KM     = 50     # same metro area
DOMESTIC_MODERATE_KM = 300
DOMESTIC_HIGH_KM     = 800


class GeographicFeatures:
    """
    Computes geographic deviation for each transaction using the
    customer's rolling geographic centroid stored in BehavioralProfileStore.
    """

    def __init__(self):
        # Lightweight centroid store (separate from BehavioralProfileStore
        # to avoid circular imports)
        self._centroids: dict[str, dict] = defaultdict(
            lambda: {"lat": None, "lon": None, "n": 0}
        )

    def compute(self, transaction: dict) -> dict:
        cid  = transaction["customer_id"]
        lat  = transaction.get("latitude",  0.0)
        lon  = transaction.get("longitude", 0.0)
        city = transaction.get("city", "")

        centroid = self._centroids[cid]
        is_intl  = city in INTERNATIONAL_CITIES

        if centroid["lat"] is None:
            # No history — first transaction is baseline
            distance_km = 0.0
            geo_score   = 0.3 if is_intl else 0.0
        else:
            distance_km = haversine_km(centroid["lat"], centroid["lon"], lat, lon)

            if is_intl:
                geo_score = 0.85
            elif distance_km < DOMESTIC_SAFE_KM:
                geo_score = 0.0
            elif distance_km < DOMESTIC_MODERATE_KM:
                geo_score = 0.2
            elif distance_km < DOMESTIC_HIGH_KM:
                geo_score = 0.5
            else:
                geo_score = min(0.8 + (distance_km - DOMESTIC_HIGH_KM) / 5000, 1.0)

        # Update rolling centroid
        n = centroid["n"] + 1
        if centroid["lat"] is None:
            centroid["lat"] = lat
            centroid["lon"] = lon
        else:
            centroid["lat"] += (lat - centroid["lat"]) / n
            centroid["lon"] += (lon - centroid["lon"]) / n
        centroid["n"] = n

        return {
            "distance_from_home_km": round(distance_km, 1),
            "is_international":      is_intl,
            "city":                  city,
            "geo_score":             round(float(geo_score), 4),
        }
