/**
 * frontend/src/hooks/useFacilities.js
 *
 * Changes from original:
 *  - Exposes `isLive` boolean — true when data came from the real backend,
 *    false when falling back to mock data. Used by StatsBar live indicator.
 *  - Builds `facilityMap` (Map of id → facility) from live data for
 *    CitationPanel to resolve backend row_ids like GH-FAC-001.
 *  - Checks GET /health first to determine backend availability quickly
 *    without waiting for a full data fetch to fail.
 */
import { useState, useEffect, useRef } from 'react';
import { getFacilities, getAnomalies, getDesertZones, getHealth } from '../utils/api';

export function useFacilities() {
  const [facilities, setFacilities]   = useState([]);
  const [anomalies,  setAnomalies]    = useState([]);
  const [desertZones,setDesertZones]  = useState([]);
  const [facilityMap,setFacilityMap]  = useState(new Map());
  const [loading,    setLoading]      = useState(true);
  const [error,      setError]        = useState(null);
  const [isLive,     setIsLive]       = useState(false);   // ← new

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      // Fast health check first — determines live indicator immediately
      let backendOnline = false;
      try {
        const health  = await getHealth();
        backendOnline = health.online === true;
      } catch {
        backendOnline = false;
      }

      try {
        const [f, a, d] = await Promise.all([
          getFacilities(),
          getAnomalies(),
          getDesertZones(),
        ]);

        if (!cancelled) {
          setFacilities(f);
          setAnomalies(a);
          setDesertZones(d);

          // Build id → facility lookup for CitationPanel
          const map = new Map();
          f.forEach((fac) => {
            if (fac.id) map.set(fac.id, fac);
            // Also index by row_id format if different
            if (fac.row_id && fac.row_id !== fac.id) map.set(fac.row_id, fac);
          });
          setFacilityMap(map);

          // We're live if backend is online AND we got non-empty real data
          setIsLive(backendOnline && f.length > 0);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setIsLive(false);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  return { facilities, anomalies, desertZones, facilityMap, loading, error, isLive };
}