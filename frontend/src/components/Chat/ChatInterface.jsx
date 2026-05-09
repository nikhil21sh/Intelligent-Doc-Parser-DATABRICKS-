import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../../hooks/useChat';
import ChatBubble from './ChatBubble';
import { DEMO_QUERIES } from '../../data/mockData';
import clsx from 'clsx';

export default function ChatInterface({ demoQuery, onDemoQueryConsumed }) {
  const { messages, loading, sendMessage } = useChat();
  const [input, setInput] = useState('');
  const [animateId, setAnimateId] = useState(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const lastMsgCount = useRef(messages.length);

  // Scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    if (messages.length > lastMsgCount.current) {
      const last = messages[messages.length - 1];
      if (last.role === 'system') setAnimateId(last.id);
      lastMsgCount.current = messages.length;
    }
  }, [messages]);

  // Handle demo query injection
  useEffect(() => {
    if (demoQuery) {
      handleSend(demoQuery);
      onDemoQueryConsumed?.();
    }
  }, [demoQuery]);

  async function handleSend(text) {
    const q = (text || input).trim();
    if (!q || loading) return;
    setInput('');
    await sendMessage(q);
    inputRef.current?.focus();
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-surface-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-primary-400 animate-pulse" />
          <span className="text-sm font-semibold text-white">AI Agent</span>
          <span className="text-xs text-slate-500">LangGraph + RAG</span>
        </div>
        <span className="text-[10px] text-slate-600 font-mono">{messages.length} messages</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto chat-scroll px-4 py-4 space-y-4 min-h-0">
        {messages.map((msg) => (
          <ChatBubble
            key={msg.id}
            message={msg}
            animate={msg.id === animateId}
          />
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex gap-3 items-start chat-msg">
            <div className="w-7 h-7 rounded-lg bg-primary-700 border border-primary-600/40 flex items-center justify-center shrink-0">
              <svg className="w-4 h-4 text-primary-300 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
            <div className="glass rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1.5 items-center">
                <span className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                <span className="text-xs text-slate-500 ml-1">Analyzing…</span>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Quick prompts */}
      <div className="px-4 py-2 border-t border-surface-border">
        <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
          {DEMO_QUERIES.slice(0, 3).map((q) => (
            <button
              key={q}
              onClick={() => handleSend(q)}
              disabled={loading}
              className="shrink-0 text-[10px] px-3 py-1.5 rounded-full border border-surface-border text-slate-400 hover:text-primary-300 hover:border-primary-600/40 transition-all whitespace-nowrap disabled:opacity-40"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className="px-4 pb-4 pt-2 shrink-0">
        <div className="flex gap-2 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask about healthcare gaps, anomalies, or recommendations…"
              rows={1}
              className="w-full bg-surface-card border border-surface-border rounded-xl px-4 py-3 text-sm text-white placeholder-slate-600 resize-none focus:outline-none focus:border-primary-600/60 focus:ring-1 focus:ring-primary-600/30 transition-all leading-relaxed"
              style={{ minHeight: 44, maxHeight: 120 }}
              onInput={e => {
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
              }}
            />
          </div>
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="w-11 h-11 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center transition-all shrink-0 shadow-glow-teal"
          >
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        <p className="text-[10px] text-slate-700 mt-1.5 text-center">Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  );
}
