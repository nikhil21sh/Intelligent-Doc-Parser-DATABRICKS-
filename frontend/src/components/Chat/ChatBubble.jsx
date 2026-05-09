import React, { useState, useEffect, useRef } from 'react';
import clsx from 'clsx';
import CitationPanel from './CitationPanel';
import { parseBold } from '../../utils/helpers';

/**
 * ChatBubble — renders a single message with optional typewriter effect.
 * system messages support bold parsing, citations, and reasoning plan.
 */
export default function ChatBubble({ message, animate = false }) {
  const { role, text, citations = [], plan = [], timestamp } = message;
  const isSystem = role === 'system';
  const [displayed, setDisplayed] = useState(animate ? '' : text);
  const [done, setDone] = useState(!animate);
  const [planOpen, setPlanOpen] = useState(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!animate || !isSystem) return;
    let i = 0;
    const CHUNK = 4;
    intervalRef.current = setInterval(() => {
      i += CHUNK;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) {
        setDisplayed(text);
        setDone(true);
        clearInterval(intervalRef.current);
      }
    }, 18);
    return () => clearInterval(intervalRef.current);
  }, [animate, text, isSystem]);

  const formattedTime = timestamp
    ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '';

  return (
    <div className={clsx('chat-msg flex gap-3', isSystem ? 'justify-start' : 'justify-end')}>
      {/* Avatar */}
      {isSystem && (
        <div className="w-7 h-7 rounded-lg bg-primary-700 border border-primary-600/40 flex items-center justify-center shrink-0 mt-0.5">
          <svg className="w-4 h-4 text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.347a3.45 3.45 0 00-1.058 2.41v.18a2 2 0 01-2 2h-.83a2 2 0 01-2-2v-.18a3.45 3.45 0 00-1.058-2.41l-.347-.347z" />
          </svg>
        </div>
      )}

      <div className={clsx('max-w-[85%] space-y-2', isSystem ? '' : 'items-end flex flex-col')}>
        {/* Bubble */}
        <div className={clsx(
          'rounded-2xl px-4 py-3 text-sm leading-relaxed',
          isSystem
            ? 'glass rounded-tl-sm text-slate-200'
            : 'bg-primary-600/30 border border-primary-500/30 text-white rounded-tr-sm'
        )}>
          {isSystem ? (
            <span
              className={clsx(!done && 'typewriter-cursor')}
              dangerouslySetInnerHTML={{ __html: parseBold(displayed) }}
            />
          ) : (
            <span>{text}</span>
          )}
        </div>

        {/* Reasoning plan */}
        {isSystem && plan.length > 0 && done && (
          <div className="w-full">
            <button
              onClick={() => setPlanOpen(!planOpen)}
              className="flex items-center gap-1.5 text-[10px] text-slate-500 hover:text-primary-300 transition-colors"
            >
              <svg className={clsx('w-3 h-3 transition-transform', planOpen && 'rotate-90')} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              Agent reasoning ({plan.length} steps)
            </button>
            {planOpen && (
              <div className="mt-1.5 pl-3 border-l border-primary-600/30 space-y-1 animate-fade-in">
                {plan.map((step, i) => (
                  <div key={i} className="flex items-center gap-2 text-[11px] text-slate-500">
                    <span className="w-4 h-4 rounded-full bg-primary-600/20 text-primary-400 flex items-center justify-center text-[9px] font-mono shrink-0">
                      {i + 1}
                    </span>
                    {step}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Citations */}
        {isSystem && done && citations.length > 0 && (
          <div className="w-full">
            <CitationPanel citations={citations} />
          </div>
        )}

        {/* Timestamp */}
        <div className={clsx('text-[10px] text-slate-600', isSystem ? 'pl-1' : 'pr-1')}>
          {formattedTime}
        </div>
      </div>

      {/* User avatar */}
      {!isSystem && (
        <div className="w-7 h-7 rounded-lg bg-slate-700 border border-slate-600/40 flex items-center justify-center shrink-0 mt-0.5">
          <svg className="w-4 h-4 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </div>
      )}
    </div>
  );
}
