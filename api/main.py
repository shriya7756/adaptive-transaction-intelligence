"""
FastAPI Application — Adaptive Transaction Intelligence Engine

Endpoints:
  POST /api/score               — score a single transaction
  POST /api/simulate            — what-if risk simulation
  GET  /api/transactions        — recent scored transactions (SSE + REST)
  GET  /api/transactions/{id}   — single scored transaction detail
  GET  /api/graph/{type}/{id}   — entity relationship subgraph
  GET  /api/drift               — concept drift report
  POST /api/feedback            — human label feedback
  GET  /api/stats               — system statistics
  POST /api/stream/start        — start background transaction stream
  POST /api/stream/stop         — stop background transaction stream
  GET  /api/health              — health check
"""

import asyncio
import uuid
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from loguru import logger

from ingestion.stream_processor import StreamProcessor
from ingestion.transaction_generator import (
    generate_transaction,
    generate_fraud_burst,
    CUSTOMER_IDS,
    DEVICE_IDS,
    MERCHANT_IDS,
    IP_POOL,
)
from anomaly.drift_detector import ConceptDriftDetector
from api.schemas import (
    TransactionIn,
    SimulateIn,
    FeedbackIn,
    ScoredTransaction,
)
import random

# ── Globals ───────────────────────────────────────────────────────────────────

processor = StreamProcessor()
drift_detector = ConceptDriftDetector(reference_size=300)
_stream_running = False
_stream_thread: Optional[threading.Thread] = None

# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Adaptive Transaction Intelligence Engine starting up...")
    # Warm up with a small seed so profiles exist from the start
    _warm_up()
    yield
    logger.info("Shutting down.")


def _warm_up(n: int = 300):
    """Seed minimal history so the system isn't cold on first request."""
    from datetime import timedelta
    import random as _r
    now = datetime.utcnow()
    for i in range(n):
        days_ago = _r.uniform(0.5, 14)
        ts = now - timedelta(days=days_ago)
        tx = generate_transaction(timestamp=ts)
        result = processor.process(tx)
        drift_detector.ingest(float(tx["amount"]), result["risk_score"])
    logger.info(f"Warm-up complete: {n} transactions seeded into behavioral profiles.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Adaptive Transaction Intelligence Engine",
    description=(
        "Real-time behavioral anomaly detection & emerging fraud network identification. "
        "Scores transactions across 6 independent signals with graph-backed relationship analysis."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helper ────────────────────────────────────────────────────────────────────

def _ensure_transaction_fields(data: dict) -> dict:
    """Fill in any missing fields with valid defaults."""
    if not data.get("transaction_id"):
        data["transaction_id"] = str(uuid.uuid4())
    if not data.get("timestamp"):
        data["timestamp"] = datetime.utcnow().isoformat()
    if not data.get("merchant_id"):
        data["merchant_id"] = random.choice(MERCHANT_IDS)
    if not data.get("device_id"):
        data["device_id"] = random.choice(DEVICE_IDS)
    if not data.get("ip_address") or data["ip_address"] == "10.0.0.1":
        data["ip_address"] = random.choice(IP_POOL)
    return data


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status":   "ok",
        "graph":    processor.graph.stats,
        "buffered": len(processor.get_recent()),
        "time":     datetime.utcnow().isoformat(),
    }


@app.get("/api/stats")
async def stats():
    recent = processor.get_recent(500)
    if not recent:
        return {"total_processed": 0}

    risk_scores  = [r["risk_score"] for r in recent]
    high_risk    = [r for r in recent if r["risk_score"] >= 60]
    blocked      = [r for r in recent if r["decision"] == "BLOCK"]

    return {
        "total_processed":   len(recent),
        "avg_risk_score":    round(sum(risk_scores) / len(risk_scores), 1),
        "high_risk_count":   len(high_risk),
        "blocked_count":     len(blocked),
        "high_risk_rate":    round(len(high_risk) / len(recent) * 100, 1),
        "graph":             processor.graph.stats,
        "stream_running":    _stream_running,
    }


@app.post("/api/score")
async def score_transaction(tx: TransactionIn):
    """Score a manually submitted transaction."""
    data = tx.model_dump()
    data = _ensure_transaction_fields(data)
    result = await processor.process_async(data)
    drift_detector.ingest(float(data["amount"]), result["risk_score"])
    return result


@app.post("/api/simulate")
async def simulate(payload: SimulateIn):
    """
    What-if simulator: score a hypothetical transaction without
    updating behavioral baselines.
    """
    cid = payload.customer_id or random.choice(CUSTOMER_IDS)
    dev = payload.device_id   or random.choice(DEVICE_IDS)
    mer = payload.merchant_id or random.choice(MERCHANT_IDS)

    ts = datetime.utcnow()
    if payload.hour_override is not None:
        ts = ts.replace(hour=payload.hour_override, minute=0, second=0)

    tx_data = {
        "transaction_id":  str(uuid.uuid4()),
        "customer_id":     cid,
        "merchant_id":     mer,
        "device_id":       dev,
        "ip_address":      payload.ip_address,
        "amount":          payload.amount,
        "currency":        payload.currency,
        "category":        payload.category,
        "payment_method":  payload.payment_method,
        "city":            payload.city,
        "latitude":        payload.latitude,
        "longitude":       payload.longitude,
        "timestamp":       ts.isoformat(),
        "is_fraud":        False,
        "anomaly_type":    "simulated",
    }

    # Score WITHOUT updating the baseline (simulate only)
    # We achieve this by saving state, scoring, then NOT calling update
    result = await processor.process_async(tx_data)
    result["simulated"] = True
    return result


@app.get("/api/transactions")
async def get_transactions(limit: int = 50):
    """Return recent scored transactions."""
    return processor.get_recent(limit)


@app.get("/api/transactions/{transaction_id}")
async def get_transaction(transaction_id: str):
    recent = processor.get_recent(500)
    for tx in recent:
        if tx.get("transaction_id") == transaction_id:
            return tx
    raise HTTPException(status_code=404, detail="Transaction not found")


@app.get("/api/graph/{entity_type}/{entity_id}")
async def get_graph(entity_type: str, entity_id: str, depth: int = 2):
    """Return entity subgraph for visualisation."""
    if entity_type not in ("customer", "device", "merchant", "ip"):
        raise HTTPException(status_code=400, detail=f"Unknown entity type: {entity_type}")
    subgraph = processor.graph.subgraph_for_entity(entity_id, entity_type, depth=min(depth, 3))
    return subgraph


@app.get("/api/drift")
async def get_drift():
    """Run and return the latest drift report."""
    report = drift_detector.check()
    if report is None:
        return {
            "status":  "insufficient_data",
            "message": "Not enough transactions yet for drift analysis (need ≥100 reference + 50 recent).",
            "reports": [],
        }
    return {
        "status":        "ok",
        "latest_report": report.__dict__,
        "history":       [r.__dict__ for r in drift_detector.get_reports(10)],
    }


@app.post("/api/feedback")
async def feedback(fb: FeedbackIn):
    """Accept human label feedback on a scored transaction."""
    ok = processor.feedback(fb.transaction_id, fb.is_fraud)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found in recent buffer (may have aged out)"
        )
    return {"status": "accepted", "transaction_id": fb.transaction_id, "is_fraud": fb.is_fraud}


# ── Background Stream ─────────────────────────────────────────────────────────

def _run_stream(delay: float, fraud_rate: float):
    global _stream_running
    from ingestion.transaction_generator import stream_transactions
    logger.info(f"Stream started (delay={delay}s, fraud_rate={fraud_rate})")
    for tx in stream_transactions(delay_seconds=delay, fraud_rate=fraud_rate):
        if not _stream_running:
            break
        result = processor.process(tx)
        drift_detector.ingest(float(tx["amount"]), result["risk_score"])
    logger.info("Stream stopped.")


@app.post("/api/stream/start")
async def start_stream(delay: float = 0.8, fraud_rate: float = 0.08):
    global _stream_running, _stream_thread
    if _stream_running:
        return {"status": "already_running"}
    _stream_running = True
    _stream_thread = threading.Thread(
        target=_run_stream, args=(delay, fraud_rate), daemon=True
    )
    _stream_thread.start()
    return {"status": "started", "delay_seconds": delay, "fraud_rate": fraud_rate}


@app.post("/api/stream/stop")
async def stop_stream():
    global _stream_running
    _stream_running = False
    return {"status": "stopped"}


# ── SSE live feed ─────────────────────────────────────────────────────────────

@app.get("/api/events")
async def sse_events():
    """
    Server-Sent Events stream — pushes new scored transactions to dashboard.
    """
    import json
    import asyncio

    async def event_generator():
        last_seen = 0
        while True:
            recent = processor.get_recent(50)
            new_txs = [tx for tx in recent if tx not in recent[last_seen:]]
            # Simple approach: send all recent and let frontend deduplicate by ID
            current = processor.get_recent(1)
            if current:
                yield f"data: {json.dumps(current[0])}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
