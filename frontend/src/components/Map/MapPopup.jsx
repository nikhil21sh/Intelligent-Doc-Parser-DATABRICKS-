import React from 'react';
import clsx from 'clsx';
import { getFacilityStatus } from '../../utils/helpers';

/**
 * Rendered inside a Leaflet Popup — must be lightweight (no Tailwind JIT classes
 * that are not pre-generated, since popup is injected into DOM outside React root).
 * We use inline styles sparingly + safe Tailwind classes.
 */
export default function MapPopup({ facility, onSelect }) {
  const status = getFacilityStatus(facility);

  const statusLabel = { critical: 'CRITICAL', warning: 'WARNING', good: 'OPERATIONAL' }[status];
  const statusColor = { critical: '#ef4444', warning: '#f59e0b', good: '#13a0a9' }[status];

  return (
    <div style={{ fontFamily: 'DM Sans, sans-serif', minWidth: 240, padding: 0 }}>
      {/* Top bar */}
      <div style={{ background: statusColor + '22', borderBottom: '1px solid ' + statusColor + '44', padding: '10px 14px 8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            background: statusColor,
            color: 'white',
            fontSize: 9,
            fontWeight: 700,
            padding: '2px 7px',
            borderRadius: 20,
            letterSpacing: 1,
            fontFamily: 'JetBrains Mono, monospace',
          }}>
            {statusLabel}
          </span>
          <span style={{ fontSize: 10, color: '#6b9cb0' }}>{facility.type}</span>
        </div>
        <h3 style={{ color: 'white', fontSize: 13, fontWeight: 700, margin: '6px 0 2px', fontFamily: 'Syne, sans-serif' }}>
          {facility.name}
        </h3>
        <p style={{ color: '#6b9cb0', fontSize: 11, margin: 0 }}>{facility.district}, {facility.region}</p>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', borderBottom: '1px solid #1e3a4a', padding: '8px 0' }}>
        {[
          { label: 'Doctors', val: facility.doctors },
          { label: 'Beds',    val: facility.beds    },
          { label: 'Capacity', val: facility.capacity_pct + '%' },
        ].map(({ label, val }) => (
          <div key={label} style={{ textAlign: 'center', padding: '0 8px' }}>
            <div style={{ color: 'white', fontSize: 15, fontWeight: 700, fontFamily: 'Syne, sans-serif' }}>{val}</div>
            <div style={{ color: '#6b9cb0', fontSize: 10 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Specialties */}
      <div style={{ padding: '8px 14px 6px' }}>
        <div style={{ fontSize: 9, color: '#4a7a8a', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 5, fontFamily: 'JetBrains Mono, monospace' }}>
          Specialties
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {facility.specialties.slice(0, 3).map((s) => (
            <span key={s} style={{
              background: 'rgba(19,160,169,0.15)',
              color: '#4dd8e0',
              fontSize: 10,
              padding: '2px 8px',
              borderRadius: 20,
              border: '1px solid rgba(19,160,169,0.2)',
            }}>{s}</span>
          ))}
          {facility.specialties.length > 3 && (
            <span style={{ color: '#4a7a8a', fontSize: 10, padding: '2px 4px' }}>+{facility.specialties.length - 3}</span>
          )}
        </div>
      </div>

      {/* Anomaly warning */}
      {facility.anomaly && (
        <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', margin: '6px 10px', borderRadius: 8, padding: '6px 10px' }}>
          <div style={{ color: '#ef4444', fontSize: 10, fontWeight: 700, marginBottom: 3 }}>⚠ ANOMALY DETECTED</div>
          <p style={{ color: '#fca5a5', fontSize: 10, margin: 0, lineHeight: 1.5 }}>
            {facility.anomaly_reason?.slice(0, 100)}...
          </p>
        </div>
      )}

      {/* Details button */}
      <div style={{ padding: '8px 10px 10px' }}>
        <button
          onClick={onSelect}
          style={{
            width: '100%',
            background: 'rgba(19,160,169,0.2)',
            color: '#4dd8e0',
            border: '1px solid rgba(19,160,169,0.3)',
            borderRadius: 8,
            padding: '7px 12px',
            fontSize: 11,
            fontWeight: 600,
            cursor: 'pointer',
            fontFamily: 'DM Sans, sans-serif',
          }}
        >
          View Full Details →
        </button>
      </div>
    </div>
  );
}
