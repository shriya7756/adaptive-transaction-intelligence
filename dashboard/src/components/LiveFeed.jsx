import React, { useState, useEffect, useRef } from 'react';
import { getTransactions } from '../api';
import ExplainPanel from './ExplainPanel';
import { submitFeedback } from '../api';

const CATEGORY_EMOJI = {
  grocery: '🛒', food_dining: '🍽️', fuel: '⛽', electronics: '💻',
  apparel: '👗', travel: '✈️', healthcare: '🏥', utilities: '💡',
  entertainment: '🎬', atm_cash: '🏧', jewelry: '💎', subscription: '📱',
};

function riskColor(score) {
  if (score >= 80) return 'var(--critical)';
  if (score >= 60) return 'var(--high)';
  if (score >= 30) return 'var(--medium)';
  return 'var(--low)';
}

function TxRow({ tx, onClick }) {
  const color  = riskColor(tx.risk_score);
  const emoji  = CATEGORY_EMOJI[tx.category] || '💳';
  const initials = (tx.customer_id || 'CU').substring(5, 7).toUpperCase();

  return (
    <div className="tx-row" onClick={() => onClick(tx)}>
      {/* Avatar */}
      <div className="tx-avatar" style={{ background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}>
        {emoji}
      </div>

      {/* Info */}
      <div className="tx-info">
        <div className="tx-cust">{tx.customer_id?.split('_')[0]}…{tx.customer_id?.slice(-4)}</div>
        <div className="tx-meta">{tx.city} · {tx.category} · {new Date(tx.timestamp).toLocaleTimeString('en-IN')}</div>
      </div>

      {/* Amount */}
      <div className="tx-amount">
        ₹{Number(tx.amount).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
      </div>

      {/* Badge */}
      <div>
        <span className={`badge badge-${tx.risk_level}`}>{tx.risk_level}</span>
      </div>

      {/* Score */}
      <div style={{ width: 48, textAlign: 'right', fontFamily: 'var(--font-sans)', fontSize: 16, fontWeight: 600 }}>
        {tx.risk_score}
      </div>
    </div>
  );
}

export default function LiveFeed({ filter = 'ALL' }) {
  const [transactions, setTransactions] = useState([]);
  const [selected, setSelected] = useState(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    const fetchTx = async () => {
      try {
        const res = await getTransactions(60);
        setTransactions(res.data);
      } catch (_) {}
    };
    fetchTx();
    intervalRef.current = setInterval(fetchTx, 1500);
    return () => clearInterval(intervalRef.current);
  }, []);

  const filtered = transactions.filter(tx => {
    if (filter === 'ALL')      return true;
    if (filter === 'HIGH')     return tx.risk_score >= 60;
    if (filter === 'CRITICAL') return tx.risk_score >= 80;
    return true;
  });

  const handleFeedback = async (txId, isFraud) => {
    try {
      await submitFeedback({ transaction_id: txId, is_fraud: isFraud });
      setSelected(null);
    } catch (_) {}
  };

  return (
    <div>
      {selected && (
        <ExplainPanel
          transaction={selected}
          onClose={() => setSelected(null)}
          onFeedback={handleFeedback}
        />
      )}

      <div className="tx-list">
        {filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
            No transactions yet — start the stream to begin.
          </div>
        ) : (
          filtered.map(tx => (
            <TxRow key={tx.transaction_id} tx={tx} onClick={setSelected} />
          ))
        )}
      </div>
    </div>
  );
}
