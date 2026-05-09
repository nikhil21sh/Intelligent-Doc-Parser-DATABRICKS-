/**
 * frontend/src/components/UI/StatsBar.jsx
 *
 * Changes from original:
 *  - Accepts `isLive` prop and shows LIVE DATA (green pulse) vs
 *    MOCK DATA (amber, static) so judges can immediately see if the
 *    backend is connected or the UI is running on fallback data.
 *  - All stats calculations unchanged.
 */
import React from 'react';
import { fmtNum } from '../../utils/helpers';

export default function StatsBar({ facilities, anomalies, isLive = false }) {
  const critical   = facilities.filter(f => f.anomaly).length;
  const totalBeds  = facilities.reduce((s, f) => s + (f.beds || 0), 0);
  const avgDoctors = facilities.length
    ? Math.round(facilities.reduce((s, f) => s + (f.doctors || 0), 0) / facilities.length)
    : 0;

  const stats = [
    { label: 'Facilities',    val: facilities.length,   icon: '🏥', color: 'text-primary-300' },
    { label: 'Critical Flags',val: critical,             icon: '⚠️', color: 'text-danger-400'  },
    { label: 'Total Beds',    val: fmtNum(totalBeds),   icon: '🛏',  color: 'text-slate-300'  },
    { label: 'Avg Doctors',   val: avgDoctors,           icon: '👨‍⚕️', color: 'text-slate-300'  },
    { label: 'Anomalies',     val: anomalies.length,     icon: '🔍', color: 'text-accent-400'  },
  ];

  return (
    <div className="flex items-center gap-1 px-4 py-2 bg-surface-light border-b border-surface-border overflow-x-auto shrink-0">

      {/* Live / Mock indicator */}
      <div className="flex items-center gap-1 mr-3 shrink-0">
        {isLive ? (
          <>
            <span className="w-2 h-2 rounded-full bg-primary-400 animate-pulse" />
            <span className="text-[10px] font-mono text-primary-400 font-semibold tracking-wider whitespace-nowrap">
              LIVE DATA
            </span>
          </>
        ) : (
          <>
            <span className="w-2 h-2 rounded-full bg-accent-400" />
            <span className="text-[10px] font-mono text-accent-400 font-semibold tracking-wider whitespace-nowrap">
              MOCK DATA
            </span>
          </>
        )}
      </div>

      <div className="h-4 w-px bg-surface-border mx-1 shrink-0" />

      {stats.map(({ label, val, icon, color }, i) => (
        <React.Fragment key={label}>
          {i > 0 && <div className="h-4 w-px bg-surface-border mx-2 shrink-0" />}
          <div className="flex items-center gap-1.5 whitespace-nowrap">
            <span className="text-sm">{icon}</span>
            <span className={`text-sm font-display font-bold ${color}`}>{val}</span>
            <span className="text-[10px] text-slate-600">{label}</span>
          </div>
        </React.Fragment>
      ))}
    </div>
  );
}