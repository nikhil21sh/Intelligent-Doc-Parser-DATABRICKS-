import React, { useState } from 'react';
import { FACILITIES } from '../../data/mockData';
import clsx from 'clsx';

export default function CitationPanel({ citations = [] }) {
  const [open, setOpen] = useState(false);
  if (!citations.length) return null;

  const resolved = citations.map((id) => FACILITIES.find((f) => f.id === id)).filter(Boolean);

  return (
    <div className="mt-2 border border-surface-border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 bg-surface-light hover:bg-surface-card transition-colors text-xs"
      >
        <div className="flex items-center gap-2 text-slate-400">
          <svg className="w-3.5 h-3.5 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span className="font-medium text-primary-300">{citations.length} source{citations.length > 1 ? 's' : ''} cited</span>
          <span className="text-slate-600">{citations.join(', ')}</span>
        </div>
        <svg
          className={clsx('w-3.5 h-3.5 text-slate-500 transition-transform', open && 'rotate-180')}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="border-t border-surface-border divide-y divide-surface-border animate-fade-in">
          {resolved.map((f) => (
            <div key={f.id} className="px-3 py-2.5 bg-surface flex items-start gap-3">
              <span className="font-mono text-[10px] text-primary-400 bg-primary-600/15 px-2 py-0.5 rounded mt-0.5 shrink-0">
                {f.id}
              </span>
              <div className="min-w-0">
                <div className="text-xs font-medium text-white">{f.name}</div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  {f.region} · {f.doctors} doctors · {f.beds} beds
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
