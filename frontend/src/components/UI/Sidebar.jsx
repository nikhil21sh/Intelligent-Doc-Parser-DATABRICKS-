import React from 'react';
import clsx from 'clsx';

const NAV_ITEMS = [
  { id: 'map',      label: 'Map View',     icon: MapIcon      },
  { id: 'chat',     label: 'AI Agent',     icon: ChatIcon     },
  { id: 'planning', label: 'Planning',     icon: PlanIcon     },
  { id: 'anomalies',label: 'Anomalies',    icon: AlertIcon    },
];

export default function Sidebar({ activeTab, onTabChange, anomalyCount, demoMode, onDemoToggle }) {
  return (
    <aside className="flex flex-col w-16 lg:w-56 h-screen bg-surface-light border-r border-surface-border shrink-0 z-20">
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-surface-border">
        <div className="w-8 h-8 rounded-lg bg-primary-600 flex items-center justify-center shrink-0">
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
        </div>
        <div className="hidden lg:block overflow-hidden">
          <h1 className="font-display font-bold text-base text-white leading-none">MedMap AI</h1>
          <p className="text-[10px] text-primary-400 mt-0.5 tracking-wider">DESERT INTELLIGENCE</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => {
          const active = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => onTabChange(id)}
              className={clsx(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                active
                  ? 'bg-primary-600/20 text-primary-300 border border-primary-600/30'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              )}
            >
              <Icon className={clsx('w-5 h-5 shrink-0', active ? 'text-primary-400' : 'text-slate-500')} />
              <span className="hidden lg:block">{label}</span>
              {id === 'anomalies' && anomalyCount > 0 && (
                <span className="hidden lg:flex ml-auto text-[10px] font-bold bg-danger-500 text-white w-5 h-5 rounded-full items-center justify-center">
                  {anomalyCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Demo Mode Button */}
      <div className="px-2 pb-4">
        <button
          onClick={onDemoToggle}
          className={clsx(
            'w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-semibold transition-all duration-300',
            demoMode
              ? 'bg-accent-500 text-white shadow-glow-amber'
              : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 border border-surface-border'
          )}
        >
          <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="hidden lg:block">{demoMode ? 'Demo Active' : 'Demo Mode'}</span>
        </button>
      </div>
    </aside>
  );
}

// ─── Inline icons ─────────────────────────────────────────────────────────────
function MapIcon(props) {
  return (
    <svg {...props} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
    </svg>
  );
}
function ChatIcon(props) {
  return (
    <svg {...props} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
    </svg>
  );
}
function PlanIcon(props) {
  return (
    <svg {...props} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
    </svg>
  );
}
function AlertIcon(props) {
  return (
    <svg {...props} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  );
}
