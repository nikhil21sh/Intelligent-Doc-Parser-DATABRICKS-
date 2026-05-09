import axios from 'axios';
import { FACILITIES, ANOMALIES, DESERT_ZONES, MOCK_RESPONSES } from '../data/mockData';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 8000,
  headers: { 'Content-Type': 'application/json' },
});

// ─── Helper: simulate network delay for demo realism ────────────────────────
const delay = (ms) => new Promise((r) => setTimeout(r, ms));

// ─── Facilities ──────────────────────────────────────────────────────────────
export async function getFacilities() {
  try {
    const { data } = await api.get('/facilities');
    return data;
  } catch {
    await delay(600);
    return FACILITIES;
  }
}

// ─── Anomalies ───────────────────────────────────────────────────────────────
export async function getAnomalies() {
  try {
    const { data } = await api.get('/anomalies');
    return data;
  } catch {
    await delay(400);
    return ANOMALIES;
  }
}

// ─── Desert Zones ────────────────────────────────────────────────────────────
export async function getDesertZones() {
  try {
    const { data } = await api.get('/deserts');
    return data;
  } catch {
    await delay(300);
    return DESERT_ZONES;
  }
}

// ─── Chat Query ───────────────────────────────────────────────────────────────
export async function postQuery(query) {
  try {
    const { data } = await api.post('/query', { query });
    return data;
  } catch {
    await delay(1200); // simulate agent thinking
    // Find closest matching mock response
    const key = Object.keys(MOCK_RESPONSES).find((k) =>
      k.toLowerCase().includes(query.toLowerCase().slice(0, 15))
    );
    const response = MOCK_RESPONSES[key] || {
      text: `I've analyzed the query: **"${query}"**\n\nBased on available facility data across Ghana's 16 regions, I've identified several potential areas of concern. The northern regions consistently show the highest healthcare access deficits, with doctor-to-population ratios falling far below WHO recommendations of 1:1,000.`,
      citations: ["GH-011", "GH-007", "GH-003"],
      plan: ["Parse query intent", "Search RAG knowledge base", "Filter relevant facilities", "Generate recommendation"],
    };
    return response;
  }
}
