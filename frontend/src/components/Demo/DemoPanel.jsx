import React, { useState } from 'react';
import { DEMO_QUERIES } from '../../data/mockData';
import clsx from 'clsx';

/**
 * DemoPanel — shown when Demo Mode is active.
 * Displays 5 preset queries the judge can click to run.
 */
export default function DemoPanel({ onQuery, onClose }) {
  const [hovered, setHovered] = useState(null);
  const [fired, setFired] = useState(null);

  async function handleQuery(q, i) {
    setFired(i);
    await new Promise(r => setTimeout(r, 300));
    onQuery(q);
    setFired(null);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="glass rounded-2xl w-full max-w-lg mx-4 overflow-hidden shadow-2xl border border-primary-600/20 animate-slide-up">
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full bg-accent-400 animate-pulse" />
                <span className="text-xs font-mono text-accent-400 font-semibold tracking-widest">DEMO MODE</span>
              </div>
              <h2 className="font-display text-xl font-bold text-white">Hackathon Demo</h2>
              <p className="text-sm text-slate-400 mt-1">Select a query to see MedMap AI in action</p>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center text-slate-400 hover:text-white transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Query list */}
        <div className="p-4 space-y-2">
          {DEMO_QUERIES.map((q, i) => (
            <button
              key={i}
              onClick={() => handleQuery(q, i)}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
              className={clsx(
                'w-full text-left px-4 py-3.5 rounded-xl border transition-all duration-200 flex items-center gap-3',
                fired === i
                  ? 'bg-primary-600/30 border-primary-500/50 scale-98'
                  : hovered === i
                  ? 'bg-primary-600/15 border-primary-600/30 translate-x-1'
                  : 'bg-surface-card border-surface-border hover:border-primary-600/20'
              )}
            >
              <span className="w-6 h-6 rounded-full bg-primary-600/20 text-primary-400 flex items-center justify-center text-[11px] font-mono font-bold shrink-0">
                {i + 1}
              </span>
              <span className="text-sm text-slate-200">{q}</span>
              <svg
                className={clsx('w-4 h-4 ml-auto text-primary-400 transition-opacity', hovered === i ? 'opacity-100' : 'opacity-0')}
                fill="none" viewBox="0 0 24 24" stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
          ))}
        </div>

        {/* Footer hint */}
        <div className="px-6 pb-5 pt-2">
          <p className="text-center text-[11px] text-slate-600">
            Queries run against live backend or fallback mock data · Powered by LangGraph + RAG
          </p>
        </div>
      </div>
    </div>
  );
}
