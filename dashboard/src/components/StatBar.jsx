import React, { useState, useEffect } from 'react';
import { getStats, startStream, stopStream } from '../api';

export default function StatBar({ onStreamChange }) {
  const [stats,    setStats]    = useState(null);
  const [streaming, setStreaming] = useState(false);

  const fetchStats = async () => {
    try {
      const res = await getStats();
      setStats(res.data);
      setStreaming(res.data.stream_running);
    } catch (_) {}
  };

  useEffect(() => {
    fetchStats();
    const id = setInterval(fetchStats, 2000);
    return () => clearInterval(id);
  }, []);

  const toggleStream = async () => {
    if (streaming) {
      await stopStream();
      setStreaming(false);
    } else {
      await startStream({ delay: 0.8, fraud_rate: 0.08 });
      setStreaming(true);
    }
    if (onStreamChange) onStreamChange(!streaming);
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      {stats && (
        <>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{stats.total_processed}</span> processed
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            <span style={{ color: 'var(--high)', fontWeight: 600 }}>{stats.high_risk_count}</span> high-risk
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            Avg <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{stats.avg_risk_score}</span>
          </div>
        </>
      )}
      <button
        className={`stream-badge ${streaming ? 'running' : 'stopped'}`}
        onClick={toggleStream}
      >
        <div className={`pulse-dot ${streaming ? '' : 'stopped'}`} />
        {streaming ? 'Stream Live' : 'Stream Paused'}
      </button>
    </div>
  );
}
