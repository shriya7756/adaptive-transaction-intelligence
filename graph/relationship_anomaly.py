"""
Relationship Anomaly Detector — Graph-based suspicious pattern detection.

Signals:
  1. Shared device: device linked to many unrelated customers
  2. Shared IP: IP linked to many unrelated customers
  3. High device degree: device connected to unusual number of merchants
  4. relationship_score: composite 0–1
"""

from graph.graph_store import TransactionGraph


# Thresholds
DEVICE_CUSTOMER_ALERT   = 3     # device shared by ≥3 customers → suspicious
IP_CUSTOMER_ALERT       = 4     # IP shared by ≥4 customers → suspicious
DEVICE_MERCHANT_ALERT   = 10    # device connected to ≥10 distinct merchants


class RelationshipAnomalyDetector:

    def __init__(self, graph: TransactionGraph):
        self._graph = graph

    def score(self, transaction: dict) -> float:
        dev   = transaction["device_id"]
        ip    = transaction["ip_address"]
        cid   = transaction["customer_id"]

        # ── Signal 1: Shared device ────────────────────────────────────────
        dev_customers = self._graph.customers_sharing_device(dev)
        n_dev_custs   = len(dev_customers)
        shared_dev_score = min((n_dev_custs - 1) / DEVICE_CUSTOMER_ALERT, 1.0) if n_dev_custs > 1 else 0.0

        # ── Signal 2: Shared IP ────────────────────────────────────────────
        ip_customers  = self._graph.customers_sharing_ip(ip)
        n_ip_custs    = len(ip_customers)
        shared_ip_score = min((n_ip_custs - 1) / IP_CUSTOMER_ALERT, 1.0) if n_ip_custs > 1 else 0.0

        # ── Signal 3: Device merchant degree ──────────────────────────────
        dev_degree = self._graph.node_degree(dev, "device")
        dev_deg_score = min(dev_degree / DEVICE_MERCHANT_ALERT, 1.0)

        # ── Composite ─────────────────────────────────────────────────────
        rel_score = 0.45 * shared_dev_score + 0.35 * shared_ip_score + 0.20 * dev_deg_score

        return round(float(rel_score), 4)

    def explain(self, transaction: dict) -> list[str]:
        """Return human-readable relationship anomaly reasons."""
        dev  = transaction["device_id"]
        ip   = transaction["ip_address"]
        reasons = []

        dev_customers = self._graph.customers_sharing_device(dev)
        if len(dev_customers) >= DEVICE_CUSTOMER_ALERT:
            reasons.append(
                f"Device linked to {len(dev_customers)} distinct accounts "
                f"(threshold: {DEVICE_CUSTOMER_ALERT})"
            )

        ip_customers = self._graph.customers_sharing_ip(ip)
        if len(ip_customers) >= IP_CUSTOMER_ALERT:
            reasons.append(
                f"IP address shared by {len(ip_customers)} distinct accounts "
                f"(threshold: {IP_CUSTOMER_ALERT})"
            )

        dev_degree = self._graph.node_degree(dev, "device")
        if dev_degree >= DEVICE_MERCHANT_ALERT:
            reasons.append(
                f"Device connected to {dev_degree} distinct merchants "
                f"(threshold: {DEVICE_MERCHANT_ALERT})"
            )

        return reasons
