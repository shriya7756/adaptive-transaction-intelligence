import React, { useState, useEffect } from 'react';
import LiveFeed     from './components/LiveFeed';
import Simulator    from './components/Simulator';
import GraphView    from './components/GraphView';
import DriftMonitor from './components/DriftMonitor';
import StatBar      from './components/StatBar';
import { getStats, getTransactions } from './api';

// ── Nav items ─────────────────────────────────────────────────────────────────
const NAV = [
  { id: 'feed',      label: 'Live Feed',       icon: '📡' },
  { id: 'simulator', label: 'Risk Simulator',   icon: '🎛️' },
  { id: 'graph',     label: 'Entity Graph',     icon: '🕸️' },
  { id: 'drift',     label: 'Drift Monitor',    icon: '📊' },
];

// ── Stat tiles ────────────────────────────────────────────────────────────────
function StatTiles({ stats }) {
  if (!stats) return null;
  const tiles = [
    { label: 'Processed',      value: stats.total_processed,  sub: 'transactions',     color: 'var(--accent)' },
    { label: 'High Risk',      value: stats.high_risk_count,  sub: `${stats.high_risk_rate}% of total`, color: 'var(--high)' },
    { label: 'Avg Risk Score', value: stats.avg_risk_score,   sub: 'out of 100',       color: stats.avg_risk_score >= 50 ? 'var(--critical)' : 'var(--low)' },
    { label: 'Graph Nodes',    value: stats.graph?.total_nodes || 0, sub: 'entities tracked', color: 'var(--accent3)' },
  ];
  return (
    <div className="stat-grid">
      {tiles.map(t => (
        <div key={t.label} className="stat-tile">
          <div className="stat-tile-label">{t.label}</div>
          <div className="stat-tile-value" style={{ color: t.color }}>{t.value}</div>
          <div className="stat-tile-sub">{t.sub}</div>
        </div>
      ))}
    </div>
  );
}

// ── Graph entity picker ───────────────────────────────────────────────────────
function GraphPicker({ onSelect }) {
  const [type, setType]   = useState('customer');
  const [id,   setId]     = useState('');
  const [options, setOpts] = useState([]);

  useEffect(() => {
    // Grab customer/device IDs from recent transactions
    getTransactions(200).then(res => {
      const txs = res.data;
      let ids = [];
      if (type === 'customer')  ids = [...new Set(txs.map(t => t.customer_id))];
      if (type === 'device')    ids = [...new Set(txs.map(t => t.device_id))];
      if (type === 'merchant')  ids = [...new Set(txs.map(t => t.merchant_id))];
      setOpts(ids.slice(0, 40));
      if (ids.length) setId(ids[0]);
    }).catch(() => {});
  }, [type]);

  return (
    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
      <select className="sim-select" style={{ width: 140 }} value={type} onChange={e => setType(e.target.value)}>
        {['customer','device','merchant'].map(t => <option key={t} value={t}>{t}</option>)}
      </select>
      <select className="sim-select" style={{ flex: 1 }} value={id} onChange={e => setId(e.target.value)}>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
      <button className="btn btn-accent" onClick={() => onSelect(type, id)}>Load Graph</button>
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [page,  setPage]  = useState('feed');
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState('ALL');
  const [graphEntity, setGraphEntity] = useState({ type: 'customer', id: null });

  useEffect(() => {
    const fetchStats = async () => {
      try { const r = await getStats(); setStats(r.data); } catch (_) {}
    };
    fetchStats();
    const id = setInterval(fetchStats, 3000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="app-layout">
      {/* ── Top bar ── */}
      <header className="topbar">
        <div className="topbar-logo">
          <div className="logo-icon">⚡</div>
          <div>
            <div>Adaptive Transaction Intelligence</div>
            <div style={{ fontSize: 10, fontWeight: 400, color: 'var(--text-muted)', letterSpacing: '0.5px' }}>
              EMERGING FRAUD NETWORK DETECTION
            </div>
          </div>
        </div>
        <div className="topbar-right">
          <StatBar />
        </div>
      </header>

      {/* ── Sidebar ── */}
      <nav className="sidebar">
        <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', padding: '4px 12px 8px', fontWeight: 600 }}>
          Navigation
        </div>
        {NAV.map(n => (
          <div
            key={n.id}
            className={`nav-item ${page === n.id ? 'active' : ''}`}
            onClick={() => setPage(n.id)}
          >
            <span style={{ fontSize: 16 }}>{n.icon}</span>
            {n.label}
          </div>
        ))}

        {/* ── System info ── */}
        <div style={{ marginTop: 'auto', padding: '12px', borderTop: '1px solid var(--border)' }}>
          {stats && (
            <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.8 }}>
              <div>🕸 {stats.graph?.total_nodes || 0} nodes</div>
              <div>🔗 {stats.graph?.total_edges || 0} edges</div>
              <div>📥 {stats.graph?.total_transactions || 0} total tx</div>
            </div>
          )}
        </div>
      </nav>

      {/* ── Main ── */}
      <main className="main-content">

        {/* ── FEED page ── */}
        {page === 'feed' && (
          <>
            <StatTiles stats={stats} />

            {/* Feed filters */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">📡 Live Transaction Stream</span>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
                  {['ALL', 'HIGH', 'CRITICAL'].map(f => (
                    <button
                      key={f}
                      className="btn"
                      style={{
                        padding: '4px 12px',
                        background: filter === f ? 'var(--text-primary)' : 'var(--bg-primary)',
                        border: '1px solid var(--border)',
                        color: filter === f ? 'var(--bg-primary)' : 'var(--text-primary)'
                      }}
                      onClick={() => setFilter(f)}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>
              <LiveFeed filter={filter} />
            </div>
          </>
        )}

        {/* ── SIMULATOR page ── */}
        {page === 'simulator' && (
          <div className="card">
            <div className="card-header">
              <span className="card-title">🎛️ What-If Risk Simulator</span>
              <span className="card-subtitle">Adjust parameters to see real-time risk scoring</span>
            </div>
            <Simulator />
          </div>
        )}

        {/* ── GRAPH page ── */}
        {page === 'graph' && (
          <div className="card">
            <div className="card-header">
              <span className="card-title">🕸️ Entity Relationship Graph</span>
              <span className="card-subtitle">2-hop subgraph from selected entity</span>
            </div>
            <GraphPicker onSelect={(type, id) => setGraphEntity({ type, id })} />
            {graphEntity.id ? (
              <GraphView entityId={graphEntity.id} entityType={graphEntity.type} />
            ) : (
              <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
                Select an entity above and click "Load Graph"
              </div>
            )}
          </div>
        )}

        {/* ── DRIFT page ── */}
        {page === 'drift' && (
          <div className="card">
            <div className="card-header">
              <span className="card-title">📊 Concept Drift Monitor</span>
              <span className="card-subtitle">PSI · KS Statistic · Distribution Shift</span>
            </div>
            <DriftMonitor />
          </div>
        )}

      </main>
    </div>
  );
}
