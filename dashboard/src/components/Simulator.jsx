import React, { useState } from 'react';
import { simulate } from '../api';
import ExplainPanel from './ExplainPanel';

const CITIES = [
  { name: 'Hyderabad', lat: 17.3850, lon: 78.4867 },
  { name: 'Bangalore', lat: 12.9716, lon: 77.5946 },
  { name: 'Mumbai',    lat: 19.0760, lon: 72.8777 },
  { name: 'Delhi',     lat: 28.7041, lon: 77.1025 },
  { name: 'Chennai',   lat: 13.0827, lon: 80.2707 },
  { name: 'Dubai',     lat: 25.2048, lon: 55.2708 },
  { name: 'London',    lat: 51.5074, lon: -0.1278 },
];

const CATEGORIES = ['grocery','food_dining','fuel','electronics','apparel','travel','healthcare','jewelry','subscription'];

function SignalBar({ label, value }) {
  const pct = Math.round((value || 0) * 100);
  const color =
    pct >= 80 ? 'var(--critical)' :
    pct >= 60 ? 'var(--high)' :
    pct >= 30 ? 'var(--medium)' :
    'var(--low)';
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr 40px', alignItems: 'center', gap: 10, marginBottom: 8 }}>
      <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{label}</span>
      <div style={{ height: 4, background: 'var(--border-light)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, transition: 'width 0.6s cubic-bezier(0.34,1.56,0.64,1)' }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 700, fontFamily: 'var(--mono)', color, textAlign: 'right' }}>{pct}</span>
    </div>
  );
}

export default function Simulator() {
  const [form, setForm] = useState({
    amount:         2000,
    city:           'Hyderabad',
    category:       'grocery',
    payment_method: 'UPI',
    hour_override:  13,
    new_device:     false,
  });
  const [result,  setResult]  = useState(null);
  const [loading, setLoading] = useState(false);
  const [detail,  setDetail]  = useState(false);

  const cityObj = CITIES.find(c => c.name === form.city) || CITIES[0];

  const handleChange = (field, value) =>
    setForm(prev => ({ ...prev, [field]: value }));

  const run = async () => {
    setLoading(true);
    setResult(null);
    try {
      const payload = {
        amount:         parseFloat(form.amount),
        city:           form.city,
        latitude:       cityObj.lat,
        longitude:      cityObj.lon,
        category:       form.category,
        payment_method: form.payment_method,
        hour_override:  parseInt(form.hour_override),
        device_id:      form.new_device ? 'DEV_ffffffff' : undefined,
      };
      const res = await simulate(payload);
      setResult(res.data);
    } catch (e) {
      alert('API error — is the backend running on port 8000?');
    } finally {
      setLoading(false);
    }
  };

  const scoreColor = result ? (
    result.risk_score >= 80 ? 'var(--critical)' :
    result.risk_score >= 60 ? 'var(--high)' :
    result.risk_score >= 30 ? 'var(--medium)' :
    'var(--low)'
  ) : 'var(--accent)';

  return (
    <div>
      {detail && result && (
        <ExplainPanel transaction={result} onClose={() => setDetail(false)} />
      )}

      <div className="sim-grid">
        {/* Amount slider */}
        <div className="sim-field" style={{ gridColumn: '1 / -1' }}>
          <label className="sim-label">
            Transaction Amount: ₹{Number(form.amount).toLocaleString('en-IN')}
          </label>
          <input
            type="range" className="sim-input"
            min={100} max={200000} step={100}
            value={form.amount}
            onChange={e => handleChange('amount', e.target.value)}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)' }}>
            <span>₹100</span><span style={{ color: 'var(--accent)' }}>₹{Number(form.amount).toLocaleString('en-IN')}</span><span>₹2,00,000</span>
          </div>
        </div>

        {/* City */}
        <div className="sim-field">
          <label className="sim-label">City / Location</label>
          <select className="sim-select" value={form.city} onChange={e => handleChange('city', e.target.value)}>
            {CITIES.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
          </select>
        </div>

        {/* Category */}
        <div className="sim-field">
          <label className="sim-label">Merchant Category</label>
          <select className="sim-select" value={form.category} onChange={e => handleChange('category', e.target.value)}>
            {CATEGORIES.map(c => <option key={c} value={c}>{c.replace('_', ' ')}</option>)}
          </select>
        </div>

        {/* Payment */}
        <div className="sim-field">
          <label className="sim-label">Payment Method</label>
          <select className="sim-select" value={form.payment_method} onChange={e => handleChange('payment_method', e.target.value)}>
            {['UPI', 'Credit Card', 'Debit Card', 'Wallet', 'NEFT'].map(m =>
              <option key={m} value={m}>{m}</option>
            )}
          </select>
        </div>

        {/* Hour */}
        <div className="sim-field">
          <label className="sim-label">Hour of Day: {form.hour_override}:00</label>
          <input
            type="range" className="sim-input"
            min={0} max={23} step={1}
            value={form.hour_override}
            onChange={e => handleChange('hour_override', e.target.value)}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)' }}>
            <span>00:00</span>
            <span style={{ color: form.hour_override >= 22 || form.hour_override <= 5 ? 'var(--critical)' : 'var(--accent)' }}>
              {form.hour_override}:00
            </span>
            <span>23:00</span>
          </div>
        </div>

        {/* New device toggle */}
        <div className="sim-field" style={{ gridColumn: '1 / -1', flexDirection: 'row', alignItems: 'center', gap: 14 }}>
          <div
            onClick={() => handleChange('new_device', !form.new_device)}
            style={{
              width: 44, height: 24,
              background: form.new_device ? 'var(--text-primary)' : 'var(--bg-primary)',
              border: '1px solid var(--border)',
              cursor: 'pointer', position: 'relative', transition: 'background 0.2s',
            }}
          >
            <div style={{
              position: 'absolute', top: 2, left: form.new_device ? 22 : 2,
              width: 18, height: 18, background: form.new_device ? 'var(--bg-primary)' : 'var(--border)',
              transition: 'left 0.2s',
            }} />
          </div>
          <span className="sim-label" style={{ marginBottom: 0 }}>
            Unknown / New Device
            {form.new_device && <span style={{ color: 'var(--critical)', marginLeft: 8 }}>⚠ High anomaly signal</span>}
          </span>
        </div>
      </div>

      {/* Run button */}
      <div style={{ marginTop: 20 }}>
        <button className="sim-btn" onClick={run} disabled={loading} style={{ width: '100%' }}>
          {loading ? '⏳ Scoring…' : '▶  Simulate Transaction Risk'}
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="sim-result">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Risk Score</div>
              <div style={{ fontSize: 52, fontWeight: 800, color: scoreColor, fontFamily: 'var(--mono)', lineHeight: 1, letterSpacing: -1 }}>
                {result.risk_score}
                <span style={{ fontSize: 20, fontWeight: 400, color: 'var(--text-secondary)' }}>/100</span>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ marginBottom: 6 }}>
                <span className={`badge badge-${result.risk_level}`}>{result.risk_level}</span>
              </div>
              <div style={{
                fontSize: 18, fontWeight: 700,
                color: result.decision === 'BLOCK' ? 'var(--critical)' : result.decision === 'SAFE' ? 'var(--low)' : 'var(--medium)'
              }}>
                {result.decision}
              </div>
            </div>
          </div>

          {/* Signal bars */}
          <div style={{ marginBottom: 16 }}>
            {result.signals && Object.entries(result.signals).map(([k, v]) => (
              <SignalBar key={k} label={k.charAt(0).toUpperCase() + k.slice(1)} value={v} />
            ))}
          </div>

          {/* Top reason */}
          {result.reasons?.length > 0 && (
            <div style={{ padding: '10px 14px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13 }}>
              <span style={{ marginRight: 8 }}>
                {result.reasons[0].severity === 'CRITICAL' ? '🔴' : result.reasons[0].severity === 'HIGH' ? '🟠' : '🟡'}
              </span>
              {result.reasons[0].reason}
            </div>
          )}

          <button className="btn" style={{ marginTop: 14, width: '100%' }} onClick={() => setDetail(true)}>
            View Full Explanation →
          </button>
        </div>
      )}
    </div>
  );
}
