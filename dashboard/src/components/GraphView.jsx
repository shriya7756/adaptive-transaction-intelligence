import React, { useState, useEffect, useRef } from 'react';
import { getGraph } from '../api';

const TYPE_COLORS = {
  customer: '#6366f1',
  device:   '#06b6d4',
  merchant: '#22c55e',
  ip:       '#f59e0b',
};
const TYPE_SHAPES = {
  customer: 'circle',
  device:   'square',
  merchant: 'diamond',
  ip:       'dot',
};

export default function GraphView({ entityId, entityType = 'customer' }) {
  const containerRef = useRef(null);
  const networkRef   = useRef(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  useEffect(() => {
    if (!entityId) return;
    setLoading(true);
    setError(null);

    getGraph(entityType, entityId)
      .then(async res => {
        const { nodes, edges } = res.data;
        if (!nodes.length) { setError('No graph data for this entity.'); return; }

        // Dynamic import to avoid SSR issues
        const { Network, DataSet } = await import('vis-network/standalone');

        const visNodes = new DataSet(nodes.map(n => ({
          id:    n.id,
          label: n.label?.substring(0, 10) || n.id.substring(0, 10),
          title: `${n.type}: ${n.label}`,
          color: { background: TYPE_COLORS[n.type] || '#64748b', border: '#fff' },
          shape: 'box',
          margin: 10,
          borderWidth: 1,
          color: { background: 'var(--bg-primary)', border: 'var(--border)' },
          font: { color: 'var(--text-primary)', face: 'var(--font-sans)', size: 12 },
        })));

        const visEdges = new DataSet(edges.map((e, i) => ({
          id:     i,
          from:   e.source,
          to:     e.target,
          color:  { color: 'var(--border-light)', highlight: 'var(--text-primary)' },
          width:  1,
          smooth: { type: 'continuous' },
        })));

        const options = {
          nodes: {
            shape: 'box',
            margin: 10,
            borderWidth: 1,
            font: { color: 'var(--text-primary)', face: 'var(--font-sans)', size: 12 },
            color: { background: 'var(--bg-primary)', border: 'var(--border)' },
          },
          edges: {
            color:  { color: 'var(--border-light)', highlight: 'var(--text-primary)' },
            width: 1,
            smooth: { type: 'continuous' }
          },
          physics: {
            solver: 'forceAtlas2Based',
            forceAtlas2Based: { gravitationalConstant: -60, centralGravity: 0.01, springLength: 100, springConstant: 0.08 }
          },
          interaction: { hover: true, tooltipDelay: 200 },
        };

        if (networkRef.current) networkRef.current.destroy();
        networkRef.current = new Network(containerRef.current, { nodes: visNodes, edges: visEdges }, options);
      })
      .catch(() => setError('Could not load graph. Is the API running?'))
      .finally(() => setLoading(false));

    return () => { if (networkRef.current) networkRef.current.destroy(); };
  }, [entityId, entityType]);

  return (
    <div>
      {loading && (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
          Building entity graph…
        </div>
      )}
      {error && (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>{error}</div>
      )}
      <div id="graph-container" ref={containerRef} style={{ display: loading || error ? 'none' : 'block' }} />
      {/* Legend */}
      <div style={{ display: 'flex', gap: 16, marginTop: 12, flexWrap: 'wrap' }}>
        {Object.entries(TYPE_COLORS).map(([type, color]) => (
          <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
            <div style={{ width: 10, height: 10, border: '1px solid var(--border)', background: color }} />
            <span style={{ color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 600 }}>{type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
