"""
Graph Builder — Extracts entity relationships from transactions and
adds them to the TransactionGraph.

Relationships added per transaction:
  customer ↔ device
  customer ↔ merchant
  customer ↔ ip
  device   ↔ merchant
  device   ↔ ip
"""

from graph.graph_store import TransactionGraph


class GraphBuilder:

    def __init__(self, graph: TransactionGraph):
        self._graph = graph

    def ingest(self, transaction: dict):
        cid   = transaction["customer_id"]
        dev   = transaction["device_id"]
        merch = transaction["merchant_id"]
        ip    = transaction["ip_address"]
        ts    = transaction["timestamp"]
        amt   = float(transaction["amount"])

        edges = [
            ("customer", cid,   "device",   dev,   amt),
            ("customer", cid,   "merchant", merch, amt),
            ("customer", cid,   "ip",       ip,    amt),
            ("device",   dev,   "merchant", merch, amt),
            ("device",   dev,   "ip",       ip,    amt),
        ]
        for src_t, src_id, dst_t, dst_id, w in edges:
            self._graph.add_edge(src_t, src_id, dst_t, dst_id, weight=w, timestamp=ts)
