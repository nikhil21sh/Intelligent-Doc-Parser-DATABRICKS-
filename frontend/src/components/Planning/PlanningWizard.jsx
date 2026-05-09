import React, { useState } from 'react';
import clsx from 'clsx';

const REGIONS = [
  'Greater Accra', 'Ashanti', 'Northern', 'Upper East', 'Upper West',
  'Volta', 'Central', 'Western', 'Bono', 'Savannah', 'Oti', 'North East',
];

const SPECIALTIES = [
  'Cardiology', 'Oncology', 'Neurology', 'Pediatrics', 'Obstetrics',
  'Orthopedics', 'Emergency Medicine', 'Psychiatry', 'Ophthalmology', 'Radiology',
];

const CONSTRAINTS = [
  'Budget < $500K', 'Budget $500K–$2M', 'Budget > $2M',
  'Mobile clinic only', 'Permanent facility', 'Telemedicine-first',
  'Within 6 months', 'Within 1 year', 'Multi-year phased',
];

const STEPS = ['Region', 'Specialty', 'Constraints', 'Review', 'Recommendation'];

export default function PlanningWizard() {
  const [step, setStep]           = useState(0);
  const [region, setRegion]       = useState('');
  const [specialty, setSpecialty] = useState('');
  const [constraints, setConstraints] = useState([]);
  const [loading, setLoading]     = useState(false);
  const [result, setResult]       = useState(null);

  function toggleConstraint(c) {
    setConstraints(prev => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c]);
  }

  async function generateRecommendation() {
    setLoading(true);
    await new Promise(r => setTimeout(r, 2000));
    setResult({
      summary: `Based on your selection of **${region}** with a focus on **${specialty}**, and the constraints you've specified, our AI recommends the following intervention:`,
      actions: [
        `Establish a **specialist outpost** in ${region} Region with 2 full-time ${specialty} physicians`,
        `Deploy **mobile diagnostic unit** covering 4 districts with X-ray and ultrasound capability`,
        `Implement **telemedicine link** to Korle Bu Teaching Hospital for specialist consultation`,
        `Train **25 community health workers** to identify and refer cases within 48 hours`,
      ],
      impact: {
        population: Math.floor(Math.random() * 200000) + 80000,
        facilities: Math.floor(Math.random() * 4) + 2,
        timeline: constraints.includes('Within 6 months') ? '5–6 months' : constraints.includes('Within 1 year') ? '9–12 months' : '18–24 months',
        cost: constraints.includes('Budget < $500K') ? '$380K' : constraints.includes('Budget $500K–$2M') ? '$1.2M' : '$3.4M',
      },
    });
    setLoading(false);
    setStep(4);
  }

  return (
    <div className="flex flex-col h-full p-4 animate-fade-in">
      {/* Step indicators */}
      <div className="flex items-center justify-between mb-6 relative">
        <div className="absolute top-3.5 left-0 right-0 h-px bg-surface-border z-0" />
        {STEPS.map((label, i) => (
          <div key={i} className="relative z-10 flex flex-col items-center gap-1.5">
            <button
              onClick={() => i < step && setStep(i)}
              className={clsx(
                'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all',
                i < step  ? 'step-done text-white cursor-pointer'
                : i === step ? 'step-active text-primary-300'
                : 'step-pending text-slate-600 cursor-default'
              )}
            >
              {i < step ? (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              ) : i + 1}
            </button>
            <span className={clsx('text-[10px] font-medium', i === step ? 'text-primary-300' : 'text-slate-600')}>
              {label}
            </span>
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="flex-1 overflow-y-auto space-y-4 min-h-0">

        {/* Step 0: Region */}
        {step === 0 && (
          <StepWrapper title="Select Target Region" sub="Which region needs intervention?">
            <div className="grid grid-cols-2 gap-2">
              {REGIONS.map(r => (
                <OptionButton key={r} selected={region === r} onClick={() => setRegion(r)}>{r}</OptionButton>
              ))}
            </div>
          </StepWrapper>
        )}

        {/* Step 1: Specialty */}
        {step === 1 && (
          <StepWrapper title="Select Medical Specialty" sub="Which specialty gap are you addressing?">
            <div className="grid grid-cols-2 gap-2">
              {SPECIALTIES.map(s => (
                <OptionButton key={s} selected={specialty === s} onClick={() => setSpecialty(s)}>{s}</OptionButton>
              ))}
            </div>
          </StepWrapper>
        )}

        {/* Step 2: Constraints */}
        {step === 2 && (
          <StepWrapper title="Select Constraints" sub="Choose all that apply">
            <div className="space-y-2">
              {['Budget', 'Facility Type', 'Timeline'].map((group, gi) => (
                <div key={group}>
                  <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-1.5">{group}</div>
                  <div className="flex flex-wrap gap-2">
                    {CONSTRAINTS.slice(gi * 3, gi * 3 + 3).map(c => (
                      <button
                        key={c}
                        onClick={() => toggleConstraint(c)}
                        className={clsx(
                          'text-xs px-3 py-1.5 rounded-lg border transition-all',
                          constraints.includes(c)
                            ? 'bg-primary-600/25 border-primary-500/50 text-primary-300'
                            : 'border-surface-border text-slate-400 hover:text-white hover:border-slate-500'
                        )}
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </StepWrapper>
        )}

        {/* Step 3: Review */}
        {step === 3 && (
          <StepWrapper title="Review Your Inputs" sub="Confirm before generating recommendation">
            <div className="space-y-3">
              {[
                { label: 'Region', val: region },
                { label: 'Specialty', val: specialty },
                { label: 'Constraints', val: constraints.join(', ') || 'None selected' },
              ].map(({ label, val }) => (
                <div key={label} className="glass rounded-xl p-3">
                  <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{label}</div>
                  <div className="text-sm text-white font-medium">{val}</div>
                </div>
              ))}
            </div>
          </StepWrapper>
        )}

        {/* Step 4: Recommendation */}
        {step === 4 && result && (
          <div className="space-y-4 animate-slide-up">
            <div className="text-center pb-2">
              <div className="w-12 h-12 rounded-full bg-primary-600/20 border border-primary-600/30 flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="font-display text-lg font-bold text-white">Recommendation Ready</h3>
              <p className="text-xs text-slate-400 mt-1">{result.summary}</p>
            </div>

            {/* Actions */}
            <div className="space-y-2">
              {result.actions.map((action, i) => (
                <div key={i} className="glass rounded-xl p-3 flex items-start gap-3">
                  <span className="w-5 h-5 rounded-full bg-primary-600/30 text-primary-300 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">{i + 1}</span>
                  <span
                    className="text-xs text-slate-300 leading-relaxed"
                    dangerouslySetInnerHTML={{
                      __html: action.replace(/\*\*(.+?)\*\*/g, '<strong class="text-white">$1</strong>')
                    }}
                  />
                </div>
              ))}
            </div>

            {/* Impact metrics */}
            <div className="glass rounded-xl p-4">
              <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-3">Estimated Impact</div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'People Served', val: result.impact.population.toLocaleString() },
                  { label: 'New Facilities', val: result.impact.facilities },
                  { label: 'Timeline', val: result.impact.timeline },
                  { label: 'Est. Cost', val: result.impact.cost },
                ].map(({ label, val }) => (
                  <div key={label}>
                    <div className="font-display text-base font-bold text-primary-300">{val}</div>
                    <div className="text-[10px] text-slate-500">{label}</div>
                  </div>
                ))}
              </div>
            </div>

            <button onClick={() => { setStep(0); setResult(null); setRegion(''); setSpecialty(''); setConstraints([]); }}
              className="w-full py-2.5 rounded-xl border border-surface-border text-xs text-slate-400 hover:text-white hover:border-slate-500 transition-all">
              Start New Plan
            </button>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-12 gap-4">
            <div className="relative w-12 h-12">
              <div className="absolute inset-0 rounded-full border-2 border-primary-600/20" />
              <div className="absolute inset-0 rounded-full border-2 border-primary-400 border-t-transparent animate-spin" />
            </div>
            <div className="text-sm text-slate-400">AI generating recommendation…</div>
          </div>
        )}
      </div>

      {/* Navigation */}
      {step < 4 && !loading && (
        <div className="flex gap-2 pt-4 border-t border-surface-border mt-4">
          {step > 0 && (
            <button
              onClick={() => setStep(s => s - 1)}
              className="flex-1 py-2.5 rounded-xl border border-surface-border text-sm text-slate-400 hover:text-white transition-all"
            >
              Back
            </button>
          )}
          <button
            onClick={step === 3 ? generateRecommendation : () => setStep(s => s + 1)}
            disabled={
              (step === 0 && !region) ||
              (step === 1 && !specialty)
            }
            className="flex-1 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-30 disabled:cursor-not-allowed text-sm font-semibold text-white transition-all"
          >
            {step === 3 ? 'Generate Recommendation' : 'Continue →'}
          </button>
        </div>
      )}
    </div>
  );
}

function StepWrapper({ title, sub, children }) {
  return (
    <div className="animate-slide-up">
      <h3 className="font-display text-base font-bold text-white mb-0.5">{title}</h3>
      <p className="text-xs text-slate-500 mb-4">{sub}</p>
      {children}
    </div>
  );
}

function OptionButton({ children, selected, onClick }) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full text-left px-3 py-2.5 rounded-xl border text-sm transition-all',
        selected
          ? 'bg-primary-600/25 border-primary-500/50 text-primary-200 font-medium'
          : 'border-surface-border text-slate-400 hover:text-white hover:border-slate-600'
      )}
    >
      {children}
    </button>
  );
}
