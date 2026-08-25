"""
Seed Transactions — Bootstraps the behavioral profiles with historical data
so the system has meaningful baselines from startup.

Run once before starting the API:
  python data/seed_transactions.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta
import random
from ingestion.transaction_generator import (
    generate_transaction,
    generate_fraud_burst,
    CUSTOMER_IDS,
)
from ingestion.stream_processor import StreamProcessor
from loguru import logger


def seed(n_normal: int = 2000, n_fraud_bursts: int = 10):
    """
    Generate historical transactions to warm up behavioral profiles.
    Uses a backdated timestamp spread over the past 30 days.
    """
    logger.info(f"Seeding {n_normal} normal + {n_fraud_bursts} fraud bursts...")

    processor = StreamProcessor()
    now = datetime.utcnow()

    # ── Normal transactions (past 30 days) ────────────────────────────────
    for i in range(n_normal):
        days_ago  = random.uniform(0.5, 30)
        ts        = now - timedelta(days=days_ago)
        tx        = generate_transaction(timestamp=ts)
        processor.process(tx)
        if (i + 1) % 500 == 0:
            logger.info(f"  {i+1}/{n_normal} normal transactions seeded")

    # ── Fraud bursts ──────────────────────────────────────────────────────
    for j in range(n_fraud_bursts):
        txns = generate_fraud_burst(n=random.randint(5, 10))
        for tx in txns:
            processor.process(tx)
        logger.info(f"  Fraud burst {j+1}/{n_fraud_bursts} seeded")

    logger.success(
        f"Seeding complete. Graph: {processor.graph.stats}. "
        f"Recent buffer: {len(processor.get_recent())} transactions."
    )
    return processor


if __name__ == "__main__":
    seed()
