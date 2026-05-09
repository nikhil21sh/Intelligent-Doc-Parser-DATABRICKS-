import React, { useEffect, useState } from 'react';

const MESSAGES = [
  'Connecting to Databricks…',
  'Loading facility index…',
  'Running anomaly detection…',
  'Initializing RAG pipeline…',
  'Rendering map layers…',
];

export default function LoadingScreen() {
  const [msgIdx, setMsgIdx] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setMsgIdx(i => Math.min(i + 1, MESSAGES.length - 1));
    }, 600);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="fixed inset-0 mesh-bg flex flex-col items-center justify-center z-50">
      {/* Logo */}
      <div className="flex items-center gap-3 mb-12">
        <div className="w-12 h-12 rounded-2xl bg-primary-600 flex items-center justify-center shadow-glow-teal">
          <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
        </div>
        <div>
          <h1 className="font-display text-3xl font-bold text-white tracking-tight">MedMap AI</h1>
          <p className="text-xs text-primary-400 tracking-widest font-mono">MEDICAL DESERT INTELLIGENCE</p>
        </div>
      </div>

      {/* Spinner */}
      <div className="relative w-16 h-16 mb-8">
        <div className="absolute inset-0 rounded-full border-2 border-primary-900" />
        <div className="absolute inset-0 rounded-full border-2 border-primary-400 border-t-transparent animate-spin" />
        <div className="absolute inset-2 rounded-full border border-primary-700 border-b-transparent animate-spin" style={{ animationDirection: 'reverse', animationDuration: '0.8s' }} />
      </div>

      {/* Status message */}
      <div className="h-5 text-center">
        <p className="text-xs text-slate-500 font-mono animate-fade-in" key={msgIdx}>
          {MESSAGES[msgIdx]}
        </p>
      </div>

      {/* Progress dots */}
      <div className="flex gap-1.5 mt-6">
        {MESSAGES.map((_, i) => (
          <div
            key={i}
            className={`w-1.5 h-1.5 rounded-full transition-all duration-500 ${
              i <= msgIdx ? 'bg-primary-400' : 'bg-surface-border'
            }`}
          />
        ))}
      </div>

      {/* Hackathon badge */}
      <div className="absolute bottom-8 flex items-center gap-2 text-[10px] text-slate-600 font-mono">
        <span>Databricks × Accenture Hackathon</span>
        <span>·</span>
        <span>Virtue Foundation</span>
      </div>
    </div>
  );
}
