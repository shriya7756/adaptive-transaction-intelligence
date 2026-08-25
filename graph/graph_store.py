"""
Transaction Graph Store — NetworkX-backed dynamic entity relationship graph.

Nodes: Customer, Device, Merchant, IP, Card (card = customer+payment_method)
Edges: Weighted by frequency, timestamped

Supports:
  - Adding relationships from incoming transactions
  - Querying neighbors for any entity
  - Community detection (for cluster anomaly)
  - Serialisation to JSON (for API / dashboard)
"""

import threading
from datetime import datetime
from typing import Optional
import networkx as nx


NODE_TYPES = {"customer", "device", "merchant", "ip"}


class TransactionGraph:
    """Thread-safe NetworkX multigraph of entity relationships."""

    def __init__(self):
        self._g: nx.Graph = nx.Graph()
        self._lock = threading.Lock()
        self._edge_count = 0

    # ── Mutating ──────────────────────────────────────────────────────────

    def add_edge(
        self,
        src_id: str, src_type: str,
        dst_id: str, dst_type: str,
        weight: float = 1.0,
        timestamp: Optional[str] = None,
    ):
        with self._lock:
            src_key = f"{src_type}:{src_id}"
            dst_key = f"{dst_type}:{dst_id}"

            if not self._g.has_node(src_key):
                self._g.add_node(src_key, entity_type=src_type, entity_id=src_id)
            if not self._g.has_node(dst_key):
                self._g.add_node(dst_key, entity_type=dst_type, entity_id=dst_id)

            if self._g.has_edge(src_key, dst_key):
                self._g[src_key][dst_key]["weight"]    += weight
                self._g[src_key][dst_key]["last_seen"]  = timestamp or datetime.utcnow().isoformat()
                self._g[src_key][dst_key]["tx_count"]  += 1
            else:
                self._g.add_edge(
                    src_key, dst_key,
                    weight=weight,
                    tx_count=1,
                    first_seen=timestamp or datetime.utcnow().isoformat(),
                    last_seen=timestamp  or datetime.utcnow().isoformat(),
                )
            self._edge_count += 1

    # ── Querying ──────────────────────────────────────────────────────────

    def neighbors(self, entity_id: str, entity_type: str) -> list[dict]:
        key = f"{entity_type}:{entity_id}"
        with self._lock:
            if not self._g.has_node(key):
                return []
            result = []
            for n in self._g.neighbors(key):
                ndata = self._g.nodes[n]
                edata = self._g[key][n]
                result.append({
                    "node":       n,
                    "type":       ndata.get("entity_type"),
                    "id":         ndata.get("entity_id"),
                    "weight":     edata.get("weight", 1),
                    "tx_count":   edata.get("tx_count", 1),
                    "first_seen": edata.get("first_seen"),
                    "last_seen":  edata.get("last_seen"),
                })
            return result

    def node_degree(self, entity_id: str, entity_type: str) -> int:
        key = f"{entity_type}:{entity_id}"
        with self._lock:
            if not self._g.has_node(key):
                return 0
            return self._g.degree(key)

    def customers_sharing_device(self, device_id: str) -> list[str]:
        """Return all customer IDs that have used a specific device."""
        dev_key = f"device:{device_id}"
        with self._lock:
            if not self._g.has_node(dev_key):
                return []
            return [
                self._g.nodes[n]["entity_id"]
                for n in self._g.neighbors(dev_key)
                if self._g.nodes[n].get("entity_type") == "customer"
            ]

    def customers_sharing_ip(self, ip: str) -> list[str]:
        ip_key = f"ip:{ip}"
        with self._lock:
            if not self._g.has_node(ip_key):
                return []
            return [
                self._g.nodes[n]["entity_id"]
                for n in self._g.neighbors(ip_key)
                if self._g.nodes[n].get("entity_type") == "customer"
            ]

    def subgraph_for_entity(self, entity_id: str, entity_type: str, depth: int = 2) -> dict:
        """
        Return a 2-hop subgraph around an entity for visualisation.
        Returns {nodes: [...], edges: [...]}
        """
        key = f"{entity_type}:{entity_id}"
        with self._lock:
            if not self._g.has_node(key):
                return {"nodes": [], "edges": []}
            ego = nx.ego_graph(self._g, key, radius=depth)
            nodes = [
                {
                    "id":    n,
                    "type":  ego.nodes[n].get("entity_type", "unknown"),
                    "label": ego.nodes[n].get("entity_id", n),
                }
                for n in ego.nodes
            ]
            edges = [
                {
                    "source":   u,
                    "target":   v,
                    "weight":   ego[u][v].get("weight", 1),
                    "tx_count": ego[u][v].get("tx_count", 1),
                }
                for u, v in ego.edges
            ]
            return {"nodes": nodes, "edges": edges}

    @property
    def stats(self) -> dict:
        with self._lock:
            return {
                "total_nodes": self._g.number_of_nodes(),
                "total_edges": self._g.number_of_edges(),
                "total_transactions": self._edge_count,
            }
