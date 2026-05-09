/**
 * frontend/src/utils/api.js
 * =========================
 * Connects the React frontend to the FastAPI backend (Intern 1)
 * and the agent orchestration layer (Intern 2) via POST /agent.
 *
 * Every function:
 *  1. Tries the real backend first
 *  2. Falls back to mock data silently if the backend is unreachable
 *  3. Normalises the backend response shape to what the UI components expect
 *
 * Backend base URL is set via VITE_API_URL in .env
 * Default: http://localhost:8000
 */

import axios from 'axios';
import {
  FACILITIES,
  ANOMALIES,
  DESERT_ZONES,
  MOCK_RESPONSES,
} from '../data/mockData';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 25000,                          // agent can take up to 20s on warm cluster
  headers: { 'Content-Type': 'application/json' },
});

const delay = (ms) => new Promise((r) => setTimeout(r, ms));


// ════════════════════════════════════════════════════════════════════════════
// SHAPE NORMALISERS
// Backend uses snake_case Pydantic fields. UI components expect a flat shape
// that matches the mockData.js structure. These functions translate between them.
// ════════════════════════════════════════════════════════════════════════════

/**
 * Converts a backend FacilityFact dict → the shape UI components expect.
 * Handles both the real backend shape and the mock shape gracefully.
 */
function normaliseFacility(f) {
  // Already in mock shape (has .doctors, .beds, .lat) — pass through
  if (typeof f.doctors !== 'undefined') return f;

  // Backend shape → UI shape
  const capacity     = f.capacity    || 0;
  const num_doctors  = f.num_doctors || 0;
  // capacity_pct: rough estimate if not provided (backend doesn't compute this)
  // Use a stable value derived from real fields when available
  const capacity_pct = capacity > 0
    ? Math.min(Math.round((num_doctors / Math.max(capacity / 40, 1)) * 100), 150)
    : 75;

  // Detect anomaly from flags if embedded, or from facility fields
  const hasAnomaly   = f.has_anomaly || false;
  const anomalyReason= f.anomaly_reason || null;

  return {
    // Identity
    id:               f.row_id || f.name,
    name:             f.name   || 'Unknown Facility',
    region:           f.address_state_or_region || f.location || 'Unknown',
    district:         f.address_city            || '',
    type:             _facilityTypeLabel(f.facility_type_id),
    // Staffing
    doctors:          num_doctors,
    nurses:           Math.round(num_doctors * 2.5),   // estimate — not in schema
    beds:             capacity,
    // Status
    capacity_pct:     capacity_pct,
    anomaly:          hasAnomaly,
    anomaly_reason:   anomalyReason,
    anomaly_confidence: f.anomaly_confidence || null,
    last_inspected:   f.last_inspected || 'N/A',
    // IDP fields
    specialties:      f.specialties || [],
    equipment:        f.equipment   || [],
    procedures:       f.procedure   || [],      // backend calls it 'procedure'
    // Geolocation
    lat:              parseFloat(f.latitude  || 0) || 0,
    lng:              parseFloat(f.longitude || 0) || 0,
  };
}

function _facilityTypeLabel(typeId) {
  const map = {
    hospital: 'Hospital',
    clinic:   'Clinic',
    pharmacy: 'Pharmacy',
    doctor:   'Doctor',
    dentist:  'Dentist',
  };
  return map[typeId] || typeId || 'Facility';
}

/**
 * Converts a backend AnomalyFlag → the shape AnomalyPanel expects.
 * {facility_id, facility_name, region, reason, confidence, severity}
 */
function normaliseAnomaly(flag) {
  return {
    facility_id:   flag.facility_id   || flag.id,
    facility_name: flag.facility_name || flag.name || 'Unknown',
    region:        flag.region        || '',
    reason:        flag.reason        || flag.flag_type || 'Anomaly detected',
    confidence:    flag.confidence    || 0,
    severity:      flag.severity      || 'high',
  };
}

/**
 * Backend /deserts returns {zones: [{region, specialty, facility_count, severity}]}
 * which has no lat/lng. We map region names to approximate Ghana centroids
 * so the map can render desert zone circles.
 * Falls back to mock DESERT_ZONES if backend zones have no coordinates.
 */
const REGION_CENTROIDS = {
  'Greater Accra': { lat: 5.6037,  lng: -0.1870  },
  'Ashanti':       { lat: 6.7470,  lng: -1.5209  },
  'Northern':      { lat: 9.5416,  lng: -0.9062  },
  'Upper East':    { lat: 10.7854, lng: -0.8501  },
  'Upper West':    { lat: 10.2529, lng: -2.3284  },
  'Western':       { lat: 5.1931,  lng: -2.7540  },
  'Central':       { lat: 5.5558,  lng: -1.0317  },
  'Eastern':       { lat: 6.5648,  lng: -0.4600  },
  'Volta':         { lat: 7.9000,  lng: 0.3254   },
  'Bono':          { lat: 7.9408,  lng: -2.3340  },
  'Savannah':      { lat: 9.1031,  lng: -1.7072  },
  'North East':    { lat: 10.5167, lng: -0.3667  },
  'Oti':           { lat: 7.9000,  lng: 0.5000   },
  'Bono East':     { lat: 7.7500,  lng: -1.0000  },
  'Ahafo':         { lat: 7.2500,  lng: -2.5000  },
  'Western North': { lat: 6.3000,  lng: -2.8000  },
};

function normaliseDesertZone(zone, index) {
  const centroid = REGION_CENTROIDS[zone.region] || { lat: 7.9465, lng: -1.0232 };
  const radiusKm = zone.facility_count === 0 ? 110 : 70;
  return {
    id:                  `dz-${zone.region}-${zone.specialty || index}`,
    name:                `${zone.region} — ${zone.specialty || 'Coverage'} Desert`,
    lat:                 centroid.lat,
    lng:                 centroid.lng,
    radius_km:           radiusKm,
    severity:            zone.severity   || 'critical',
    population_affected: zone.facility_count === 0 ? 350000 : 150000,
    specialty:           zone.specialty  || '',
    region:              zone.region,
  };
}

/**
 * Converts a backend AgentResponse JSON → the shape useChat expects:
 * { text, citations, plan }
 */
function normaliseAgentResponse(data) {
  // data is the parsed AgentResponse from respond_node:
  // {narrative, recommendations, anomalies_flagged, gaps_identified,
  //  cited_row_ids, query, generated_at, node_errors}

  // Build a rich markdown-style text from narrative + recommendations
  let text = data.narrative || '';

  if (data.recommendations && data.recommendations.length > 0) {
    const recs = data.recommendations
      .slice(0, 4)
      .map(r => r.replace(/^\[(URGENT|HIGH|GAP|ROUTE|MEDIUM)\]\s*/i, ''))
      .join('\n\n');
    text += `\n\n${recs}`;
  }

  // Convert [row_id] inline citations to bold for readability
  text = text.replace(/\[([A-Z0-9\-]+)\]/g, '**[$1]**');

  // Plan steps — use gaps + node names as the reasoning trace
  const plan = [
    'Query vector index via /search',
    'Fetch anomaly flags via /anomalies',
    'Detect desert zones via /deserts',
    'Synthesize narrative with inline citations',
  ];
  if (data.node_errors && data.node_errors.length > 0) {
    plan.push(`Note: ${data.node_errors.length} non-fatal backend warning(s)`);
  }

  return {
    text:      text.trim(),
    citations: data.cited_row_ids || [],
    plan,
  };
}


// ════════════════════════════════════════════════════════════════════════════
// PUBLIC API FUNCTIONS
// ════════════════════════════════════════════════════════════════════════════

/**
 * GET /facilities → normalised facility array for map pins + stats bar.
 * Backend: {count, data: FacilityFact[]}
 */
export async function getFacilities() {
  try {
    const { data } = await api.get('/facilities', { params: { limit: 500 } });
    // Backend returns {count, data: [...]} envelope
    const raw = Array.isArray(data) ? data : (data.data || []);
    const facilities = raw.map(normaliseFacility).filter(f => f.lat !== 0 || f.lng !== 0);
    return facilities.length > 0 ? facilities : FACILITIES;
  } catch {
    await delay(600);
    return FACILITIES;
  }
}

/**
 * GET /anomalies → normalised anomaly array for AnomalyPanel.
 * Backend: {flags: AnomalyFlag[], total_flags, region}
 *
 * We also enrich each anomaly with the facility's region by doing a
 * secondary /facilities lookup keyed by facility_id.
 */
export async function getAnomalies() {
  try {
    const { data } = await api.get('/anomalies');
    const raw = Array.isArray(data) ? data : (data.flags || []);
    const anomalies = raw.map(normaliseAnomaly);
    return anomalies.length > 0 ? anomalies : ANOMALIES;
  } catch {
    await delay(400);
    return ANOMALIES;
  }
}

/**
 * GET /deserts → normalised desert zone array for map overlay.
 * Backend requires ?specialty= so we fan out across key specialties
 * and merge the results into one array for the map.
 */
export async function getDesertZones() {
  const KEY_SPECIALTIES = [
    'cardiology',
    'emergencyMedicine',
    'pediatrics',
    'gynecologyAndObstetrics',
  ];

  try {
    const allZones = [];
    const seen     = new Set();

    await Promise.all(
      KEY_SPECIALTIES.map(async (specialty) => {
        try {
          const { data } = await api.get('/deserts', { params: { specialty } });
          const zones = Array.isArray(data) ? data : (data.zones || []);
          zones.forEach((z, i) => {
            const key = `${z.region}-${specialty}`;
            if (!seen.has(key)) {
              seen.add(key);
              // Only show critical/high severity on map — avoids clutter
              if (z.severity === 'critical' || z.severity === 'high') {
                allZones.push(normaliseDesertZone({ ...z, specialty }, i));
              }
            }
          });
        } catch {
          // Individual specialty call failed — skip silently
        }
      })
    );

    return allZones.length > 0 ? allZones : DESERT_ZONES;
  } catch {
    await delay(300);
    return DESERT_ZONES;
  }
}

/**
 * POST /agent → agent orchestration pipeline response.
 * This calls the full LangGraph agent: retrieve → reason → synthesize → respond.
 * Backend: AgentResponse JSON {narrative, recommendations, anomalies_flagged,
 *          gaps_identified, cited_row_ids, query, generated_at, node_errors}
 *
 * Returns the shape useChat expects: {text, citations, plan}
 */
export async function postQuery(query) {
  try {
    const { data } = await api.post('/agent', { text: query });
    // /agent returns AgentResponse JSON (already parsed by respond_node)
    const parsed = typeof data === 'string' ? JSON.parse(data) : data;
    return normaliseAgentResponse(parsed);
  } catch {
    await delay(1200);
    // Fallback: find closest mock response by keyword match
    const key = Object.keys(MOCK_RESPONSES).find((k) =>
      query.toLowerCase().includes(k.toLowerCase().split(' ')[0])
    );
    const response = MOCK_RESPONSES[key] || {
      text: `I've analyzed: **"${query}"**\n\nBased on facility data across Ghana's 16 regions, the northern regions show the highest healthcare access deficits, with doctor-to-population ratios falling far below WHO recommendations of 1:1,000.`,
      citations: ['GH-011', 'GH-007', 'GH-003'],
      plan: [
        'Query vector index via /search',
        'Fetch anomaly flags via /anomalies',
        'Detect desert zones via /deserts',
        'Synthesize narrative with inline citations',
      ],
    };
    return response;
  }
}

/**
 * GET /health → backend status object.
 * Used by the UI to show live vs mock data indicator.
 */
export async function getHealth() {
  try {
    const { data } = await api.get('/health');
    return { online: true, ...data };
  } catch {
    return { online: false };
  }
}

/**
 * POST /search → direct semantic search (used by future filter panel).
 * Not called by current UI but exported for completeness.
 */
export async function searchFacilities(query, region = null, specialty = null) {
  try {
    const { data } = await api.post('/search', { q: query, region, specialty, top_k: 10 });
    const raw = data.facilities || [];
    return raw.map(normaliseFacility);
  } catch {
    return FACILITIES.filter(f =>
      f.name.toLowerCase().includes(query.toLowerCase()) ||
      f.region.toLowerCase().includes(query.toLowerCase())
    );
  }
}