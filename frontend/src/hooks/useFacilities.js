import { useState, useEffect } from 'react';
import { getFacilities, getAnomalies, getDesertZones } from '../utils/api';

export function useFacilities() {
  const [facilities, setFacilities]   = useState([]);
  const [anomalies, setAnomalies]     = useState([]);
  const [desertZones, setDesertZones] = useState([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
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
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  return { facilities, anomalies, desertZones, loading, error };
}
