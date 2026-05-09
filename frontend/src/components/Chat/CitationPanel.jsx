/**
 * frontend/src/components/Chat/CitationPanel.jsx
 *
 * Changed from Day 3 original:
 *  - No longer resolves citations exclusively from FACILITIES mock.
 *  - Accepts an optional `facilityMap` prop (Map of id→facility) built
 *    from live backend data when available.
 *  - Falls back to mock FACILITIES lookup for backward compat.
 *  - When neither resolves, shows the raw row_id with a "DB record" label
 *    so citations are never silently swallowed.
 */
import React, { useState } from 'react';
import { FACILITIES } from '../../data/mockData';
import clsx from 'clsx';

export default function CitationPanel({ citations = [], facilityMap = null }) {
  const [open, setOpen] = useState(false);
  if (!citations.length) return null;

  /**
   * Resolve a citation id to a display object.
   * Priority: 1) live facilityMap   2) mock FACILITIES   3) raw id fallback
   */
  function resolve(id) {
    // 1. Live map passed from parent (populated from backend /facilities)
    if (facilityMap && facilityMap.has(id)) {
      return facilityMap.get(id);
    }
    // 2. Mock data (id format GH-001 etc.)
    const mock = FACILITIES.find((f) => f.id === id);
    if (mock) return mock;
    // 3. Raw fallback — show the row_id with a DB label
    return {
      id,
      name:    id,
      region:  'Delta Lake record',
      doctors: '—',
      beds:    '—',
      _raw:    true,
    };
  }

  const resolved = citations.map(resolve);

  return (
    <div className="mt-2 border border-surface-border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 bg-surface-light hover:bg-surface-card transition-colors text-xs"
      >
        <div className="flex items-center gap-2 text-slate-400">
          <svg className="w-3.5 h-3.5 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span className="font-medium text-primary-300">
            {citations.length} source{citations.length > 1 ? 's' : ''} cited
          </span>
          <span className="text-slate-600 truncate max-w-[160px]">
            {citations.join(', ')}
          </span>
        </div>
        <svg
          className={clsx('w-3.5 h-3.5 text-slate-500 transition-transform shrink-0', open && 'rotate-180')}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="border-t border-surface-border divide-y divide-surface-border animate-fade-in">
          {resolved.map((f) => (
            <div key={f.id} className="px-3 py-2.5 bg-surface flex items-start gap-3">
              <span className={clsx(
                'font-mono text-[10px] px-2 py-0.5 rounded mt-0.5 shrink-0',
                f._raw
                  ? 'text-accent-400 bg-accent-500/10'
                  : 'text-primary-400 bg-primary-600/15'
              )}>
                {f.id}
              </span>
              <div className="min-w-0">
                <div className="text-xs font-medium text-white truncate">{f.name}</div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  {f.region}
                  {!f._raw && ` · ${f.doctors} doctors · ${f.beds} beds`}
                  {f._raw && (
                    <span className="ml-1 text-accent-400/70">· live backend record</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}