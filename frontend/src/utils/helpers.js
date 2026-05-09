// ─── Facility classification ─────────────────────────────────────────────────

/**
 * Returns colour tier based on resource levels
 * @returns {'critical'|'warning'|'good'}
 */
export function getFacilityStatus(facility) {
  if (facility.anomaly) return 'critical';
  if (facility.doctors < 20 || facility.capacity_pct > 95) return 'warning';
  return 'good';
}

export const STATUS_COLORS = {
  critical: { fill: '#ef4444', stroke: '#dc2626', glow: 'rgba(239,68,68,0.4)' },
  warning:  { fill: '#f59e0b', stroke: '#d97706', glow: 'rgba(245,158,11,0.3)' },
  good:     { fill: '#13a0a9', stroke: '#0e808c', glow: 'rgba(19,160,169,0.3)' },
};

/** Create SVG circle marker for Leaflet DivIcon */
export function createMarkerSVG(status, size = 16) {
  const c = STATUS_COLORS[status];
  const isPulse = status === 'critical';
  return `
    <svg width="${size * 2.5}" height="${size * 2.5}" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
      ${isPulse ? `<circle cx="20" cy="20" r="18" fill="${c.glow}" class="marker-critical-ring"/>` : ''}
      <circle cx="20" cy="20" r="${size / 2 + 6}" fill="${c.glow}"/>
      <circle cx="20" cy="20" r="${size / 2}" fill="${c.fill}" stroke="${c.stroke}" stroke-width="2"/>
      <circle cx="20" cy="20" r="${size / 4}" fill="white" opacity="0.6"/>
    </svg>
  `;
}

// ─── Number formatting ────────────────────────────────────────────────────────
export function fmtNum(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000)    return (n / 1000).toFixed(0) + 'K';
  return String(n);
}

export function fmtPct(n) { return n + '%'; }

// ─── Confidence badge colour ──────────────────────────────────────────────────
export function confidenceColor(conf) {
  if (conf >= 0.95) return 'bg-danger-500';
  if (conf >= 0.85) return 'bg-accent-500';
  return 'bg-primary-500';
}

// ─── Parse markdown-style bold from agent text ───────────────────────────────
export function parseBold(text) {
  return text.replace(/\*\*(.+?)\*\*/g, '<strong class="text-primary-300 font-semibold">$1</strong>');
}

// ─── Typewriter effect helper ─────────────────────────────────────────────────
export function* typewriterGen(text, chunkSize = 3) {
  let i = 0;
  while (i < text.length) {
    yield text.slice(0, i + chunkSize);
    i += chunkSize;
  }
  yield text; // ensure full text at end
}
