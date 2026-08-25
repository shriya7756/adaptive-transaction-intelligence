# Adaptive Transaction Intelligence Engine
### Real-Time Behavioral Anomaly & Emerging Fraud Network Detection

> *"Does this transaction represent a statistically significant change in behavior — and does this entity participate in a suspicious emerging cluster?"*

---

## What makes this different

| Generic Fraud Detection | This Project |
|---|---|
| Individual transaction classifier | Behavioral entity profile engine |
| Single-event view | Multi-window (5m → 30d) rolling baselines |
| Static model | Adaptive risk scoring with concept drift detection |
| Probability score only | Signal-level breakdown + SHAP explanation |
| No graph analysis | Dynamic entity relationship graph |
| Notebook demo | Interactive React dashboard with what-if simulator |
| Detects: "Is this fraud?" | Detects: "Has this entity's behavior changed, and is it part of a suspicious network?" |

---

## Architecture

```
Transaction Generator (India-flavored synthetic data)
        │
        ▼
   In-memory Queue  ──── (optional: Kafka)
        │
   ┌────┴────┐
   ▼         ▼
Feature    Graph
Processor  Builder
   │         │
   ▼         ▼
Rolling    NetworkX
Profiles   Entity Graph
   │         │
   └────┬────┘
        ▼
   Risk Engine (6 signals, weighted composite)
   ┌────────────────────────────────────────┐
   │  Statistical:   Z-score + IQR + IF     │
   │  Behavioral:    KL divergence baseline │
   │  Velocity:      5m / 1h / 24h windows │
   │  Geographic:    Haversine distance     │
   │  Temporal:      Hour-of-day deviation  │
   │  Relationship:  Shared device/IP graph │
   └────────────────────────────────────────┘
        │
   Explanation Engine (rule-based + SHAP)
        │
   FastAPI  ◄──►  React Dashboard
        │
   Concept Drift Detector (PSI + KS)
```

---

## Quick Start

### 1. Backend (Python)

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# or: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the API (auto-seeds 300 transactions on startup)
uvicorn api.main:app --reload --port 8000
```

The API auto-seeds behavioral profiles on startup. Visit http://localhost:8000/docs for interactive API docs.

### 2. Dashboard (React)

```bash
cd dashboard
npm install
npm run dev
# Opens at http://localhost:3000
```

### 3. Start the live stream

In the dashboard, click **"Stream Paused"** in the top bar to start live transaction generation.

Or via API:
```bash
curl -X POST "http://localhost:8000/api/stream/start?fraud_rate=0.08"
```

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/score` | POST | Score a single transaction |
| `/api/simulate` | POST | What-if risk simulation (no baseline update) |
| `/api/transactions` | GET | Recent scored transactions |
| `/api/graph/{type}/{id}` | GET | Entity subgraph for visualisation |
| `/api/drift` | GET | Concept drift report (PSI + KS) |
| `/api/feedback` | POST | Label a transaction for retraining |
| `/api/stream/start` | POST | Start background transaction stream |
| `/api/stream/stop` | POST | Stop stream |
| `/api/stats` | GET | System statistics |
| `/api/health` | GET | Health check |

---

## Project Structure

```
adaptive-transaction-intelligence/
│
├── ingestion/
│   ├── transaction_generator.py   # India-flavored synthetic transactions
│   └── stream_processor.py        # Pipeline orchestrator
│
├── features/
│   ├── velocity.py                # Rolling window velocity signals
│   ├── behavioral.py              # Welford online baseline profiles
│   ├── temporal.py                # Hour-of-day anomaly signals
│   └── geographic.py              # Haversine distance signals
│
├── anomaly/
│   ├── statistical.py             # Z-score + IQR + Isolation Forest
│   ├── behavioral_drift.py        # KL divergence recent vs baseline
│   └── drift_detector.py          # PSI + KS concept drift detection
│
├── graph/
│   ├── graph_store.py             # Thread-safe NetworkX entity graph
│   ├── graph_builder.py           # Relationship extractor
│   └── relationship_anomaly.py    # Shared device/IP cluster detection
│
├── scoring/
│   ├── risk_engine.py             # Weighted composite scorer
│   └── explanation.py             # Human-readable signal reasons
│
├── api/
│   ├── main.py                    # FastAPI application
│   └── schemas.py                 # Pydantic request/response models
│
├── data/
│   └── seed_transactions.py       # Historical data seeder
│
├── dashboard/                     # React + Vite frontend
│   └── src/
│       ├── components/
│       │   ├── LiveFeed.jsx       # Real-time transaction stream
│       │   ├── ExplainPanel.jsx   # Signal breakdown + reasons modal
│       │   ├── Simulator.jsx      # What-if risk simulator
│       │   ├── GraphView.jsx      # vis-network entity graph
│       │   └── DriftMonitor.jsx   # Concept drift dashboard
│       └── App.jsx
│
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Dashboard Features

### 📡 Live Feed
- Real-time color-coded transaction stream (green → red by risk)
- Filter by ALL / HIGH / CRITICAL
- Click any transaction → full explanation modal

### 🎛️ Risk Simulator
- Adjust amount (₹100 → ₹2,00,000), city, hour, device novelty
- See all 6 signal bars update live
- Demonstrates exactly how the system thinks

### 🕸️ Entity Graph
- Select any customer, device, or merchant
- 2-hop NetworkX subgraph visualised with vis-network
- Node color = entity type; edge width = transaction frequency

### 📊 Drift Monitor
- PSI (Population Stability Index) for amount + risk distributions
- KS statistic + p-value for distribution shift significance
- "Trigger Retrain" button when drift is significant

---
