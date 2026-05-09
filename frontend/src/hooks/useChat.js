import { useState, useCallback } from 'react';
import { postQuery } from '../utils/api';

export function useChat() {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'system',
      text: "Hello! I'm **MedMap AI**, your medical desert intelligence agent. I can analyze healthcare facility data across Ghana, identify resource gaps, and recommend intervention strategies. How can I help you today?",
      citations: [],
      plan: [],
      timestamp: new Date(),
    },
  ]);
  const [loading, setLoading] = useState(false);

  const sendMessage = useCallback(async (query) => {
    const userMsg = {
      id: `u-${Date.now()}`,
      role: 'user',
      text: query,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const response = await postQuery(query);
      const sysMsg = {
        id: `s-${Date.now()}`,
        role: 'system',
        text: response.text,
        citations: response.citations || [],
        plan: response.plan || [],
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, sysMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: 'system',
          text: 'I encountered an error reaching the analysis engine. Please try again.',
          citations: [],
          plan: [],
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
  }, []);

  return { messages, loading, sendMessage, clearChat };
}
