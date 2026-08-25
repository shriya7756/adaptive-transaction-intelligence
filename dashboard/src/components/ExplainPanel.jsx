import React from 'react';

const SEVERITY_ICON = {
  CRITICAL: '🔴',
  HIGH:     '🟠',
  MEDIUM:   '🟡',
  LOW:      '🟢',
};

function SignalBar({ label, value, color }) {
  const pct = Math.round((value || 0) * 100);
  const barColor = color || (
    pct >= 80 ? 'var(--critical)' :
    pct >= 60 ? 'var(--high)' :
    pct >= 30 ? 'var(--medium)' :
    'var(--low)'
  );
  return (
    <div className="signal-row">
      <span className="signal-label">{label}</span>
      <div className="signal-bar-bg">
        <div
          className="signal-bar-fill"
          style={{ width: `${pct}%`, background: barColor }}
        />
      </div>
      <span className="signal-value" style={{ color: 'var(--text-primary)' }}>{pct}</span>
    </div>
  );
}

export default function ExplainPanel({ transaction, onClose, onFeedback }) {
  if (!transaction) return null;

  const { risk_score, risk_level, decision, signals, reasons, customer_id,
          amount, city, timestamp, merchant_id, device_id, category } = transaction;

  const scoreColor =
    risk_score >= 80 ? 'var(--critical)' :
    risk_score >= 60 ? 'var(--high)' :
    risk_score >= 30 ? 'var(--medium)' :
    'var(--low)';

  const ts = new Date(timestamp).toLocaleString('en-IN', {
    dateStyle: 'medium', timeStyle: 'short'
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ position: 'relative' }}>
        <button className="modal-close" onClick={onClose}>✕</button>

        {/* ── Hero score ── */}
        <div className="risk-score-hero">
          <div className="risk-score-number" style={{ color: 'var(--text-primary)' }}>
            {risk_score}
          </div>
          <div className="risk-score-label">
            Risk Score / 100 &nbsp;·&nbsp;
            <span className={`badge badge-${risk_level}`}>{risk_level}</span>
            &nbsp;·&nbsp;
            <span style={{ color: decision === 'BLOCK' ? 'var(--critical)' : decision === 'SAFE' ? 'var(--low)' : 'var(--medium)', fontWeight: 700 }}>
              {decision}
            </span>
          </div>
        </div>

        {/* ── Transaction meta ── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 20 }}>
          {[
            ['Customer',  customer_id?.split('_')[1] || customer_id],
            ['Amount',    `₹${Number(amount).toLocaleString('en-IN')}`],
            ['City',      city],
            ['Time',      ts],
            ['Category',  category],
            ['Merchant',  merchant_id?.split('_')[1] || merchant_id],
          ].map(([k, v]) => (
            <div key={k} style={{ padding: '8px 12px', background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{k}</div>
              <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>{v}</div>
            </div>
          ))}
        </div>

        {/* ── Signal bars ── */}
        <div className="card-header" style={{ marginBottom: 12 }}>
          <span className="card-title">Signal Breakdown</span>
        </div>
        <div className="risk-bar-wrap" style={{ marginBottom: 20 }}>
          {signals && Object.entries(signals).map(([name, val]) => (
            <SignalBar key={name} label={name.charAt(0).toUpperCase() + name.slice(1)} value={val} />
          ))}
        </div>

        {/* ── Reasons ── */}
        {reasons && reasons.length > 0 && (
          <>
            <div className="card-header" style={{ marginBottom: 12 }}>
              <span className="card-title">Why this was flagged</span>
            </div>
            <div className="reasons-list" style={{ marginBottom: 20 }}>
              {reasons.map((r, i) => (
                <div key={i} className="reason-item">
                  <span className="reason-icon">{SEVERITY_ICON[r.severity] || '⚪'}</span>
                  <div>
                    <div className="reason-text">{r.reason}</div>
                    <div className="reason-signal">{r.signal}</div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* ── Feedback ── */}
        {onFeedback && (
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <button className="btn" onClick={() => onFeedback(transaction.transaction_id, false)}>
              ✓ Mark Legitimate
            </button>
            <button className="btn" style={{ borderColor: 'var(--critical)', color: 'var(--critical)' }}
              onClick={() => onFeedback(transaction.transaction_id, true)}>
              ✗ Confirm Fraud
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
