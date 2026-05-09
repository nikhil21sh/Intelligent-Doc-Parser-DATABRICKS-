import React from 'react';
import clsx from 'clsx';
import AnomalyBadge from './AnomalyBadge';

export default function AnomalyPanel({ anomalies }) {
  if (!anomalies.length) return (
    <div className="flex flex-col items-center justify-center h-64 text-slate-500">
      <svg className="w-12 h-12 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p>No anomalies detected</p>
    </div>
  );

  const critical = anomalies.filter(a => a.severity === 'critical');
  const high     = anomalies.filter(a => a.severity === 'high');

  return (
    <div className="p-4 space-y-6 animate-fade-in">
      {/* Summary bar */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Total Flagged', val: anomalies.length, color: 'text-white' },
          { label: 'Critical',      val: critical.length,  color: 'text-danger-400' },
          { label: 'High Risk',     val: high.length,      color: 'text-accent-400' },
        ].map(({ label, val, color }) => (
          <div key={label} className="glass rounded-xl p-3 text-center">
            <div className={clsx('font-display text-2xl font-bold', color)}>{val}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {/* Anomaly list */}
      <div className="space-y-3">
        {anomalies.map((a) => (
          <div
            key={a.facility_id}
            className={clsx(
              'glass rounded-xl p-4 border-l-2 transition-all hover:border-l-4',
              a.severity === 'critical' ? 'border-danger-500' : 'border-accent-500'
            )}
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <div>
                <h3 className="font-semibold text-sm text-white">{a.facility_name}</h3>
                <p className="text-[11px] text-slate-500 mt-0.5">{a.region}</p>
              </div>
              <AnomalyBadge
                reason={a.reason}
                confidence={a.confidence}
                severity={a.severity}
                size="sm"
              />
            </div>
            <p className="text-xs text-slate-400 leading-relaxed line-clamp-2">{a.reason}</p>
            {a.confidence && (
              <div className="flex items-center gap-2 mt-3">
                <div className="flex-1 h-1 bg-surface rounded-full overflow-hidden">
                  <div
                    className={clsx('h-full rounded-full', a.severity === 'critical' ? 'bg-danger-500' : 'bg-accent-500')}
                    style={{ width: `${Math.round(a.confidence * 100)}%` }}
                  />
                </div>
                <span className="text-[10px] font-mono text-slate-500">{Math.round(a.confidence * 100)}% confidence</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
