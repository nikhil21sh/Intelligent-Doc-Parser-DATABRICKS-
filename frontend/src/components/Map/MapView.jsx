import React, { useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap, Circle } from 'react-leaflet';
import L from 'leaflet';
import MapPopup from './MapPopup';
import { getFacilityStatus, STATUS_COLORS } from '../../utils/helpers';

// ─── Heatmap layer (vanilla Leaflet, not react-leaflet) ──────────────────────
function HeatmapLayer({ facilities, visible }) {
  const map = useMap();
  const layerRef = useRef(null);

  useEffect(() => {
    if (!visible) {
      if (layerRef.current) { map.removeLayer(layerRef.current); layerRef.current = null; }
      return;
    }
    // Dynamic import of leaflet.heat
    import('leaflet.heat').then(() => {
      if (layerRef.current) map.removeLayer(layerRef.current);
      const points = facilities.map((f) => {
        const shortage = Math.max(0, 1 - f.doctors / 50);
        const overload = Math.max(0, (f.capacity_pct - 70) / 50);
        const intensity = Math.min(1, shortage * 0.6 + overload * 0.4);
        return [f.lat, f.lng, intensity];
      });
      layerRef.current = L.heatLayer(points, {
        radius: 60,
        blur: 40,
        maxZoom: 8,
        gradient: { 0: '#13a0a9', 0.4: '#f59e0b', 0.7: '#ef4444', 1: '#dc2626' },
      });
      layerRef.current.addTo(map);
    });

    return () => {
      if (layerRef.current) { map.removeLayer(layerRef.current); layerRef.current = null; }
    };
  }, [map, facilities, visible]);

  return null;
}

// ─── Auto-fit bounds ──────────────────────────────────────────────────────────
function FitBounds({ facilities }) {
  const map = useMap();
  useEffect(() => {
    if (facilities.length > 0) {
      const bounds = L.latLngBounds(facilities.map((f) => [f.lat, f.lng]));
      map.fitBounds(bounds, { padding: [60, 60] });
    }
  }, [map, facilities]);
  return null;
}

// ─── Main Map Component ───────────────────────────────────────────────────────
export default function MapView({ facilities, desertZones, onSelectFacility }) {
  const [showHeatmap, setShowHeatmap]   = useState(false);
  const [showDeserts, setShowDeserts]   = useState(true);
  const [filterStatus, setFilterStatus] = useState('all'); // 'all'|'critical'|'warning'|'good'

  const filtered = filterStatus === 'all'
    ? facilities
    : facilities.filter((f) => getFacilityStatus(f) === filterStatus);

  const SEVERITY_COLORS = {
    critical: 'rgba(239,68,68,0.12)',
    high:     'rgba(245,158,11,0.10)',
    moderate: 'rgba(19,160,169,0.08)',
  };

  return (
    <div className="relative w-full h-full flex flex-col">
      {/* Toolbar */}
      <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[1000] flex items-center gap-2 glass rounded-xl px-3 py-2 shadow-xl">
        {/* Filter pills */}
        {['all','critical','warning','good'].map((s) => (
          <button
            key={s}
            onClick={() => setFilterStatus(s)}
            className={`text-[11px] font-semibold px-3 py-1 rounded-full transition-all capitalize ${
              filterStatus === s
                ? s === 'critical' ? 'bg-danger-500 text-white'
                  : s === 'warning' ? 'bg-accent-500 text-white'
                  : s === 'good' ? 'bg-primary-600 text-white'
                  : 'bg-white/20 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            {s === 'all' ? 'All' : s}
          </button>
        ))}
        <div className="w-px h-4 bg-surface-border mx-1" />
        {/* Layer toggles */}
        <button
          onClick={() => setShowHeatmap(!showHeatmap)}
          className={`text-[11px] font-semibold px-3 py-1 rounded-full transition-all ${
            showHeatmap ? 'bg-primary-600/60 text-primary-200' : 'text-slate-400 hover:text-white'
          }`}
        >
          🌡 Heatmap
        </button>
        <button
          onClick={() => setShowDeserts(!showDeserts)}
          className={`text-[11px] font-semibold px-3 py-1 rounded-full transition-all ${
            showDeserts ? 'bg-danger-500/40 text-danger-200' : 'text-slate-400 hover:text-white'
          }`}
        >
          🏜 Deserts
        </button>
      </div>

      {/* Map */}
      <MapContainer
        center={[7.9465, -1.0232]}
        zoom={7}
        className="flex-1 w-full"
        style={{ background: '#0a2231' }}
        zoomControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          subdomains="abcd"
          maxZoom={19}
        />

        {/* Desert zones */}
        {showDeserts && desertZones.map((zone) => (
          <Circle
            key={zone.id}
            center={[zone.lat, zone.lng]}
            radius={zone.radius_km * 1000}
            pathOptions={{
              fillColor: SEVERITY_COLORS[zone.severity] || 'rgba(239,68,68,0.10)',
              fillOpacity: 1,
              color: zone.severity === 'critical' ? '#ef4444' : zone.severity === 'high' ? '#f59e0b' : '#13a0a9',
              weight: 1.5,
              dashArray: '6 4',
              opacity: 0.5,
            }}
          >
            <Popup>
              <div style={{ fontFamily: 'DM Sans, sans-serif', padding: '8px 4px' }}>
                <div style={{ color: '#ef4444', fontSize: 10, fontWeight: 700, marginBottom: 4, textTransform: 'uppercase', letterSpacing: 1 }}>
                  Medical Desert Zone
                </div>
                <div style={{ color: 'white', fontSize: 13, fontWeight: 700, marginBottom: 4 }}>{zone.name}</div>
                <div style={{ color: '#6b9cb0', fontSize: 11 }}>
                  ~{zone.population_affected.toLocaleString()} people affected
                </div>
              </div>
            </Popup>
          </Circle>
        ))}

        {/* Facility markers */}
        {filtered.map((facility) => {
          const status = getFacilityStatus(facility);
          const c = STATUS_COLORS[status];
          return (
            <CircleMarker
              key={facility.id}
              center={[facility.lat, facility.lng]}
              radius={status === 'critical' ? 10 : status === 'warning' ? 8 : 7}
              pathOptions={{
                fillColor: c.fill,
                fillOpacity: 0.9,
                color: c.stroke,
                weight: 2,
              }}
            >
              <Popup maxWidth={280} className="medmap-popup">
                <MapPopup facility={facility} onSelect={() => onSelectFacility(facility)} />
              </Popup>
            </CircleMarker>
          );
        })}

        <HeatmapLayer facilities={facilities} visible={showHeatmap} />
        {facilities.length > 0 && <FitBounds facilities={facilities} />}
      </MapContainer>

      {/* Legend */}
      <div className="absolute bottom-4 right-4 z-[1000] glass rounded-xl p-3 text-xs space-y-2">
        <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2">Legend</div>
        {[
          { color: '#ef4444', label: 'Critical / Anomaly' },
          { color: '#f59e0b', label: 'Warning' },
          { color: '#13a0a9', label: 'Operational' },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: color }} />
            <span className="text-slate-400">{label}</span>
          </div>
        ))}
        <div className="border-t border-surface-border pt-2 mt-1">
          <div className="flex items-center gap-2">
            <span className="w-6 h-px border-t-2 border-dashed border-danger-500/60" />
            <span className="text-slate-400">Desert zone</span>
          </div>
        </div>
      </div>

      {/* Facility count */}
      <div className="absolute bottom-4 left-4 z-[1000] glass rounded-xl px-3 py-2 text-xs">
        <span className="text-primary-400 font-mono font-bold">{filtered.length}</span>
        <span className="text-slate-500 ml-1">facilities shown</span>
      </div>
    </div>
  );
}
