import React from 'react';
import clsx from 'clsx';
import AnomalyBadge from '../Anomaly/AnomalyBadge';
import { getFacilityStatus, fmtNum } from '../../utils/helpers';

/**
 * FacilityCard — full card showing facility details.
 * Used in sidebar panel when a marker is clicked.
 */
export default function FacilityCard({ facility, onClose }) {
  const status = getFacilityStatus(facility);

  const statusBorder = {
    critical: 'border-danger-500/40',
    warning:  'border-accent-500/40',
    good:     'border-primary-500/40',
  }[status];

  const capacityColor = facility.capacity_pct > 100
    ? 'bg-danger-500'
    : facility.capacity_pct > 85
    ? 'bg-accent-500'
    : 'bg-primary-500';

  return (
    <div className={clsx('glass rounded-2xl overflow-hidden border animate-slide-up', statusBorder)}>
      {/* Header */}
      <div className="p-4 pb-3 border-b border-surface-border">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="font-display font-bold text-base text-white leading-tight">{facility.name}</h2>
              {facility.anomaly && (
                <AnomalyBadge
                  reason={facility.anomaly_reason}
                  confidence={facility.anomaly_confidence}
                  severity={facility.anomaly_confidence > 0.95 ? 'critical' : 'high'}
                  size="sm"
                />
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1">{facility.type} · {facility.region}</p>
          </div>
          {onClose && (
            <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors p-1">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 divide-x divide-surface-border border-b border-surface-border">
        {[
          { label: 'Doctors', val: facility.doctors, icon: '👨‍⚕️' },
          { label: 'Beds',    val: fmtNum(facility.beds), icon: '🛏' },
          { label: 'Nurses',  val: facility.nurses, icon: '👩‍⚕️' },
        ].map(({ label, val, icon }) => (
          <div key={label} className="px-3 py-2.5 text-center">
            <div className="text-lg font-display font-bold text-white">{val}</div>
            <div className="text-[10px] text-slate-500">{label}</div>
          </div>
        ))}
      </div>

      {/* Capacity bar */}
      <div className="px-4 py-3 border-b border-surface-border">
        <div className="flex justify-between text-[11px] mb-1.5">
          <span className="text-slate-500">Capacity</span>
          <span className={clsx('font-mono font-medium', facility.capacity_pct > 100 ? 'text-danger-400' : 'text-slate-300')}>
            {facility.capacity_pct}%
          </span>
        </div>
        <div className="h-1.5 bg-surface rounded-full overflow-hidden">
          <div
            className={clsx('h-full rounded-full transition-all', capacityColor)}
            style={{ width: `${Math.min(facility.capacity_pct, 100)}%` }}
          />
        </div>
      </div>

      <div className="p-4 space-y-3">
        {/* Specialties */}
        <Section title="Specialties">
          <div className="flex flex-wrap gap-1.5">
            {facility.specialties.map((s) => (
              <Tag key={s} color="teal">{s}</Tag>
            ))}
          </div>
        </Section>

        {/* Equipment */}
        <Section title="Equipment">
          <div className="flex flex-wrap gap-1.5">
            {facility.equipment.map((e) => (
              <Tag key={e} color="slate">{e}</Tag>
            ))}
          </div>
        </Section>

        {/* Procedures */}
        <Section title="Procedures">
          <div className="flex flex-wrap gap-1.5">
            {facility.procedures.map((p) => (
              <Tag key={p} color="amber">{p}</Tag>
            ))}
          </div>
        </Section>

        {/* Last inspected */}
        <div className="text-[10px] text-slate-600 pt-1 border-t border-surface-border">
          Last inspected: {facility.last_inspected}
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div>
      <h3 className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-1.5">{title}</h3>
      {children}
    </div>
  );
}

function Tag({ children, color = 'slate' }) {
  const cls = {
    teal:  'bg-primary-600/20 text-primary-300 border-primary-600/20',
    amber: 'bg-accent-500/15 text-accent-400 border-accent-500/20',
    slate: 'bg-white/5 text-slate-400 border-white/10',
  }[color];
  return (
    <span className={clsx('inline-block text-[10px] px-2 py-0.5 rounded-full border', cls)}>
      {children}
    </span>
  );
}
