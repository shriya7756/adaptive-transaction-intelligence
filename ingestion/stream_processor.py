"""
Stream Processor — Routes incoming transactions through the full pipeline:
  Feature extraction → Anomaly scoring → Risk engine → Storage
Runs as an async event loop; can be driven by Kafka or in-memory queue.
"""

import asyncio
import json
from datetime import datetime
from typing import Callable, Optional
from loguru import logger

from features.velocity import VelocityFeatures
from features.behavioral import BehavioralProfileStore
from features.temporal import TemporalFeatures
from features.geographic import GeographicFeatures
from anomaly.statistical import StatisticalAnomalyDetector
from anomaly.behavioral_drift import BehavioralDriftDetector
from graph.graph_store import TransactionGraph
from graph.graph_builder import GraphBuilder
from graph.relationship_anomaly import RelationshipAnomalyDetector
from scoring.risk_engine import RiskEngine
from scoring.explanation import ExplanationEngine


class StreamProcessor:
    """
    Central processing pipeline for incoming transactions.
    Thread-safe; can handle concurrent async calls from FastAPI.
    """

    def __init__(self):
        self.velocity        = VelocityFeatures()
        self.behavioral      = BehavioralProfileStore()
        self.temporal        = TemporalFeatures()
        self.geographic      = GeographicFeatures()
        self.stat_anomaly    = StatisticalAnomalyDetector()
        self.behav_drift     = BehavioralDriftDetector()
        self.graph           = TransactionGraph()
        self.graph_builder   = GraphBuilder(self.graph)
        self.rel_anomaly     = RelationshipAnomalyDetector(self.graph)
        self.risk_engine     = RiskEngine()
        self.explainer       = ExplanationEngine()
        self._recent: list[dict] = []   # in-memory ring buffer for dashboard
        self._max_recent = 500

    def process(self, transaction: dict) -> dict:
        """
        Process one transaction synchronously.
        Returns the enriched transaction with risk score and explanation.
        """
        cid = transaction["customer_id"]
        ts  = datetime.fromisoformat(transaction["timestamp"])

        # ── 1. Feature extraction ──────────────────────────────────────────
        vel_features  = self.velocity.compute(transaction)
        behav_features = self.behavioral.compute(transaction)
        temp_features  = self.temporal.compute(transaction)
        geo_features   = self.geographic.compute(transaction)

        # ── 2. Update graph ─────────────────────────────────────────────────
        self.graph_builder.ingest(transaction)

        # ── 3. Anomaly signals ──────────────────────────────────────────────
        stat_score  = self.stat_anomaly.score(transaction, behav_features)
        drift_score = self.behav_drift.score(transaction, behav_features)
        rel_score   = self.rel_anomaly.score(transaction)

        # ── 4. Composite risk ───────────────────────────────────────────────
        signals = {
            "statistical":    stat_score,
            "behavioral":     drift_score,
            "velocity":       vel_features.get("velocity_score", 0.0),
            "geographic":     geo_features.get("geo_score", 0.0),
            "temporal":       temp_features.get("temporal_score", 0.0),
            "relationship":   rel_score,
        }
        risk_result = self.risk_engine.score(signals, transaction)

        # ── 5. Explanation ──────────────────────────────────────────────────
        reasons = self.explainer.explain(
            transaction, signals, behav_features, vel_features, geo_features, temp_features
        )

        # ── 6. Update behavioral baseline ──────────────────────────────────
        self.behavioral.update(transaction)
        self.velocity.update(transaction)

        # ── 7. Assemble result ──────────────────────────────────────────────
        result = {
            **transaction,
            "risk_score":    round(risk_result["score"] * 100, 1),
            "risk_level":    risk_result["level"],
            "decision":      risk_result["decision"],
            "signals":       {k: round(v, 4) for k, v in signals.items()},
            "reasons":       reasons,
            "processed_at":  datetime.utcnow().isoformat(),
        }

        # Store in ring buffer
        self._recent.insert(0, result)
        if len(self._recent) > self._max_recent:
            self._recent.pop()

        level_color = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red", "CRITICAL": "red bold"}
        logger.opt(colors=True).info(
            f"[<{level_color.get(risk_result['level'], 'white')}>"
            f"{risk_result['level']}</>] "
            f"{cid} | ₹{transaction['amount']:,.0f} | "
            f"Risk {result['risk_score']}/100 | {transaction['city']}"
        )

        return result

    async def process_async(self, transaction: dict) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.process, transaction)

    def get_recent(self, limit: int = 50) -> list[dict]:
        return self._recent[:limit]

    def feedback(self, transaction_id: str, is_fraud: bool):
        """Accept human label feedback — used for drift detection and retraining."""
        for tx in self._recent:
            if tx["transaction_id"] == transaction_id:
                tx["feedback_label"] = is_fraud
                tx["feedback_at"] = datetime.utcnow().isoformat()
                logger.info(f"Feedback recorded: {transaction_id} → {'FRAUD' if is_fraud else 'LEGIT'}")
                return True
        return False
