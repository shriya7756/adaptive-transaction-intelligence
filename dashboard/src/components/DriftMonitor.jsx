import React, { useState, useEffect } from 'react';
import { getDrift } from '../api';

function MetricTile({ label, value, unit = '', color }) {
  return (
    <div className="drift-metric">
      <div className="drift-metric-label">{label}</div>
      <div className="drift-metric-value" style={{ color: color || 'var(--text-primary)' }}>
        {typeof value === 'number' ? value.toFixed(4) : value}
        {unit && <span style={{ fontSize: 14, color: 'var(--text-secondary)', marginLeft: 4 }}>{unit}</span>}
      </div>
    </div>
  );
}

const LEVEL_COLOR = {
  NONE: 'var(--low)',
  MODERATE: 'var(--medium)',
  SIGNIFICANT: 'var(--critical)',
};
const LEVEL_ICON = { NONE: '✅', MODERATE: '⚠️', SIGNIFICANT: '🚨' };

export default function DriftMonitor() {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  const fetchDrift = async () => {
    try {
      const res = await getDrift();
      setData(res.data);
      setError(null);
    } catch (_) {
      setError('Could not reach API.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDrift();
    const id = setInterval(fetchDrift, 15000);
    return () => clearInterval(id);
  }, []);

  if (loading) return <div style={{ color: 'var(--text-muted)', padding: '40px 0', textAlign: 'center' }}>Loading drift report…</div>;
  if (error)   return <div style={{ color: 'var(--text-muted)', padding: '40px 0', textAlign: 'center' }}>{error}</div>;
  if (data?.status === 'insufficient_data') return (
    <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
      <div style={{ fontSize: 32, marginBottom: 8 }}>📊</div>
      <div>{data.message}</div>
    </div>
  );

  const latest = data?.latest_report;
  const level  = latest?.alert_level || 'NONE';
  const history = data?.history || [];

  return (
    <div>
      {/* Status Banner */}
      <div className={`drift-indicator ${level}`} style={{ marginBottom: 20 }}>
        <span style={{ fontSize: 24 }}>{LEVEL_ICON[level]}</span>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: LEVEL_COLOR[level] }}>
            {level === 'NONE' ? 'No Significant Drift' :
             level === 'MODERATE' ? 'Moderate Drift Detected' :
             'Significant Drift — Retraining Recommended'}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
            {latest?.message}
          </div>
        </div>
        {latest?.should_retrain && (
          <button className="btn btn-accent" style={{ marginLeft: 'auto', whiteSpace: 'nowrap' }}>
            Trigger Retrain
          </button>
        )}
      </div>

      {/* Metrics */}
      {latest && (
        <div className="drift-metric-grid" style={{ marginBottom: 20 }}>
          <MetricTile label="PSI (Amount)"    value={latest.psi_amount}     color={latest.psi_amount >= 0.2 ? 'var(--critical)' : latest.psi_amount >= 0.1 ? 'var(--medium)' : 'var(--low)'} />
          <MetricTile label="PSI (Risk Score)" value={latest.psi_risk}      color={latest.psi_risk   >= 0.2 ? 'var(--critical)' : latest.psi_risk   >= 0.1 ? 'var(--medium)' : 'var(--low)'} />
          <MetricTile label="KS Stat (Amount)" value={latest.ks_stat_amount} />
          <MetricTile label="KS p-value"        value={latest.ks_pval_amount} color={latest.ks_pval_amount < 0.05 ? 'var(--critical)' : 'var(--low)'} />
        </div>
      )}

      {/* PSI Reference */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header"><span className="card-title">PSI Interpretation Guide</span></div>
        {[
          { range: '< 0.10', label: 'No significant change', color: 'var(--low)' },
          { range: '0.10 – 0.20', label: 'Moderate shift — monitor closely', color: 'var(--medium)' },
          { range: '> 0.20', label: 'Significant drift — consider retraining', color: 'var(--critical)' },
        ].map(row => (
          <div key={row.range} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
            <div style={{ width: 10, height: 10, border: '1px solid var(--border)', background: row.color, flexShrink: 0 }} />
            <span style={{ fontFamily: 'var(--mono)', color: row.color, minWidth: 110, fontSize: 12 }}>{row.range}</span>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{row.label}</span>
          </div>
        ))}
      </div>

      {/* History */}
      {history.length > 1 && (
        <div>
          <div className="card-header"><span className="card-title">Check History</span></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {history.slice().reverse().map((r, i) => (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '8px 12px', background: 'var(--bg-secondary)',
                border: '1px solid var(--border)', borderRadius: 8, fontSize: 12
              }}>
                <span style={{ color: 'var(--text-muted)' }}>{new Date(r.timestamp).toLocaleTimeString()}</span>
                <span style={{ color: LEVEL_COLOR[r.alert_level], fontWeight: 700 }}>{r.alert_level}</span>
                <span style={{ color: 'var(--text-secondary)' }}>PSI={r.psi_amount.toFixed(3)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
