import React, { useState } from 'react';
import clsx from 'clsx';
import { confidenceColor, fmtPct } from '../../utils/helpers';

/**
 * AnomalyBadge — shows a red/amber flag with tooltip explaining the anomaly.
 * Props:
 *   reason      : string
 *   confidence  : number (0–1)
 *   severity    : 'critical' | 'high' | 'moderate'
 *   size        : 'sm' | 'md' (default 'md')
 */
export default function AnomalyBadge({ reason, confidence, severity = 'high', size = 'md' }) {
  const [show, setShow] = useState(false);

  const label = severity === 'critical' ? 'CRITICAL' : severity === 'high' ? 'FLAGGED' : 'ALERT';
  const bg = severity === 'critical'
    ? 'bg-danger-500 hover:bg-danger-600'
    : severity === 'high'
    ? 'bg-accent-500 hover:bg-accent-600'
    : 'bg-primary-500 hover:bg-primary-600';

  return (
    <div className="relative inline-block">
      <button
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onClick={() => setShow(!show)}
        className={clsx(
          'inline-flex items-center gap-1 font-mono font-bold rounded-full text-white transition-all',
          bg,
          size === 'sm' ? 'px-2 py-0.5 text-[9px]' : 'px-2.5 py-1 text-[10px]'
        )}
      >
        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
        {label}
      </button>

      {/* Tooltip */}
      {show && reason && (
        <div className="absolute bottom-full left-0 mb-2 z-50 w-72 glass rounded-xl p-3 text-xs shadow-2xl animate-fade-in pointer-events-none">
          <div className="flex items-start gap-2 mb-2">
            <span className={clsx('w-2 h-2 rounded-full mt-0.5 shrink-0', severity === 'critical' ? 'bg-danger-400' : 'bg-accent-400')} />
            <p className="text-slate-200 leading-relaxed">{reason}</p>
          </div>
          {confidence != null && (
            <div className="flex items-center gap-2 mt-2 pt-2 border-t border-surface-border">
              <span className="text-slate-500">Confidence</span>
              <div className="flex-1 h-1.5 bg-surface rounded-full overflow-hidden">
                <div
                  className={clsx('h-full rounded-full', confidenceColor(confidence))}
                  style={{ width: fmtPct(Math.round(confidence * 100)) }}
                />
              </div>
              <span className="font-mono text-white">{Math.round(confidence * 100)}%</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
