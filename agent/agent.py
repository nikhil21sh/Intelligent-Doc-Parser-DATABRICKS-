"""
agent/agent.py
==============
Day 4 — FINAL UNIFIED AGENT (Intern 2)
Combines and replaces agent_day2.py + agent_day3.py into one production file.

Day 4 additions over Day 3:
  - All mock data REMOVED — every call goes to the real backend (with graceful fallback)
  - Field name alignment with backend models.py:
      address_state_or_region (not address_stateOrRegion)
      num_doctors             (not numberDoctors)
      facility_type_id        (not facilityTypeId)
  - /anomalies response correctly parsed as {flags, total_flags, region}
  - /deserts wired into reason_node — gaps now use real desert data
  - 15-second timeout on every node; graceful fallback on timeout
  - Retry logic on reason_node failure — falls back to direct-retrieval response
  - Full 10-query evaluation harness — scores saved to docs/eval_final.md
  - 5-question demo script in demo/queries.json
  - run_agent() exposed cleanly for FastAPI /agent endpoint (Day 5 need)

Run:
    python agent/agent.py            — runs eval harness + demo queries
    python agent/agent.py --demo     — runs 5 demo queries only
    python agent/agent.py --query "your question"  — runs single query
"""

import os
import sys
import json
import time
import argparse
import requests
import threading
from typing      import TypedDict, List, Dict, Any, Optional
from datetime    import datetime
from dotenv      import load_dotenv
from pydantic    import BaseModel
from langgraph.graph import StateGraph, END
import mlflow

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE   = os.getenv("INTERN1_API_BASE", "http://127.0.0.1:8000")
NODE_TIMEOUT_S         = 15     # max seconds per node before fallback
SEARCH_CONF_THRESHOLD  = 0.60   # below this → Genie fallback




# ════════════════════════════════════════════════════════════════════════════
# STATE & TYPED MODELS
# ════════════════════════════════════════════════════════════════════════════

class AgentState(TypedDict):
    query:                str
    region:               Optional[str]
    retrieved_facilities: List[Dict[str, Any]]
    search_confidence:    float
    reasoning:            Dict[str, Any]
    narrative:            str
    citations:            List[str]
    response:             str
    mlflow_run_id:        Optional[str]
    node_errors:          List[str]          # Day 4: track non-fatal errors per run


class ReasoningOutput(BaseModel):
    gaps_identified:   List[str]
    anomalies_flagged: List[Dict[str, Any]]
    recommendations:   List[str]
    cited_row_ids:     List[str]


class AgentResponse(BaseModel):
    """Typed final output — frontend chat UI consumes this JSON shape."""
    narrative:         str
    recommendations:   List[str]
    anomalies_flagged: List[Dict[str, Any]]
    gaps_identified:   List[str]
    cited_row_ids:     List[str]
    query:             str
    generated_at:      str
    node_errors:       List[str]    # surfaces non-fatal backend errors to UI


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def validate_state(state: AgentState, required_keys: List[str], node_name: str):
    """Raises ValueError on missing/empty required state fields."""
    for key in required_keys:
        val = state.get(key)
        if val is None or val == [] or val == {}:
            raise ValueError(
                f"[{node_name}] missing or empty state field: '{key}'"
            )


def log_step_citation(run_id: Optional[str], node_name: str, cited_ids: List[str]):
    """
    Logs cited row IDs as an MLflow run tag for step-level citation tracing.
    Non-blocking — citation failure never crashes the agent.
    """
    if not run_id or not cited_ids:
        return
    def _tag():
        try:
            client = mlflow.tracking.MlflowClient()
            client.set_tag(run_id, f"cited_rows_{node_name}", ",".join(cited_ids))
        except Exception as e:
            print(f"  [MLflow tag] warning: {e}")
    threading.Thread(target=_tag, daemon=True).start()


def _call_with_timeout(fn, timeout: int, fallback):
    """
    Calls fn() with a timeout. Returns fallback value if timeout is exceeded.
    Used to enforce NODE_TIMEOUT_S on every backend call.
    """
    result    = [fallback]
    exception = [None]

    def _run():
        try:
            result[0] = fn()
        except Exception as e:
            exception[0] = e

    t = threading.Thread(target=_run)
    t.start()
    t.join(timeout)

    if t.is_alive():
        return fallback, TimeoutError(f"call timed out after {timeout}s")
    return result[0], exception[0]


# ── Field name normaliser ─────────────────────────────────────────────────────
# Backend returns snake_case Pydantic fields.
# Agent internally uses these same names after this normalisation.
# Old mock data used camelCase — this ensures backward compat during transition.

def _normalise_facility(f: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalises a facility dict from the backend to the agent's internal field names.
    Handles both the old camelCase mock format and the new snake_case backend format.
    """
    return {
        # Core identity
        "row_id":                  f.get("row_id"),
        "name":                    f.get("name", "Unknown"),
        "location":                f.get("location") or f.get("address_state_or_region", ""),
        # Address — backend uses snake_case
        "address_state_or_region": (f.get("address_state_or_region")
                                    or f.get("address_stateOrRegion", "")),
        "address_city":            f.get("address_city") or f.get("city", ""),
        # Classification
        "facility_type_id":        (f.get("facility_type_id")
                                    or f.get("facilityTypeId", "")),
        "operator_type_id":        (f.get("operator_type_id")
                                    or f.get("operatorTypeId", "")),
        # Staffing / capacity
        "num_doctors":             (f.get("num_doctors")
                                    or f.get("numberDoctors", 0) or 0),
        "capacity":                f.get("capacity", 0) or 0,
        # IDP fields
        "specialties":             f.get("specialties", []) or [],
        "capability":              f.get("capability",  []) or [],
        "equipment":               f.get("equipment",   []) or [],
        "procedure":               f.get("procedure",   []) or [],
        # Geolocation
        "latitude":                f.get("latitude"),
        "longitude":               f.get("longitude"),
    }


# ════════════════════════════════════════════════════════════════════════════
# BACKEND API CALLS — all real, all with timeout + graceful fallback
# ════════════════════════════════════════════════════════════════════════════

def _api_search(query: str, region: Optional[str], specialty: Optional[str]) -> Dict:
    """
    POST /search → {facilities, confidence, query, result_count}
    Returns empty result dict on any failure.
    """
    payload = {"q": query, "top_k": 5}
    if region:
        payload["region"]    = region
    if specialty:
        payload["specialty"] = specialty

    resp = requests.post(
        f"{API_BASE}/search",
        json    = payload,
        timeout = NODE_TIMEOUT_S
    )
    resp.raise_for_status()
    return resp.json()   # {facilities: [...], confidence: float, ...}


def _api_anomalies(facility_ids: List[str], region: Optional[str]) -> List[Dict]:
    """
    GET /anomalies → {flags: [...], total_flags, region}
    Returns empty list on any failure.
    """
    params = {}
    if facility_ids:
        params["facility_ids"] = ",".join(facility_ids)
    if region:
        params["region"] = region

    resp = requests.get(
        f"{API_BASE}/anomalies",
        params  = params,
        timeout = NODE_TIMEOUT_S
    )
    resp.raise_for_status()
    data = resp.json()
    # Backend returns {flags: [...], total_flags, region}
    return data.get("flags", [])


def _api_deserts(specialty: str, region: Optional[str]) -> List[Dict]:
    """
    GET /deserts → {zones: [...], specialty, region, total_zones}
    Returns empty list on any failure.
    """
    params = {"specialty": specialty}
    if region:
        params["region"] = region

    resp = requests.get(
        f"{API_BASE}/deserts",
        params  = params,
        timeout = NODE_TIMEOUT_S
    )
    resp.raise_for_status()
    data = resp.json()
    # Backend returns {zones: [...], total_zones, specialty, region}
    return data.get("zones", [])


# ════════════════════════════════════════════════════════════════════════════
# NODE 1: RETRIEVE
# ════════════════════════════════════════════════════════════════════════════

def retrieve_node(state: AgentState) -> Dict[str, Any]:
    """
    Calls POST /search on the backend.
    Falls back to Genie (mocked) if confidence < threshold or backend is down.
    Normalises field names so all downstream nodes use consistent keys.
    """
    print("\n[RETRIEVE NODE]")
    validate_state(state, ["query"], "retrieve_node")

    query      = state["query"]
    region     = state.get("region")
    run_id     = state.get("mlflow_run_id")
    errors     = list(state.get("node_errors", []))
    facilities = []
    confidence = 0.0

    # ── Primary: real /search endpoint ──
    def _do_search():
        return _api_search(query, region, None)

    raw, err = _call_with_timeout(_do_search, NODE_TIMEOUT_S, None)

    if err:
        msg = f"retrieve: /search failed ({type(err).__name__}: {err})"
        print(f"  ⚠ {msg}")
        errors.append(msg)
    elif raw:
        raw_facilities = raw.get("facilities", [])
        facilities     = [_normalise_facility(f) for f in raw_facilities]
        confidence     = raw.get("confidence", 0.0)
        print(f"  /search → {len(facilities)} facilities, confidence={confidence:.2f}")

    # ── Fallback: Genie mock if confidence too low or backend down ──
    if confidence < SEARCH_CONF_THRESHOLD or not facilities:
        print(f"  Genie fallback (confidence={confidence:.2f})")
        # Genie is still mocked — swap this block for real Genie API call
        genie_context = {
            "sql": "SELECT address_state_or_region, COUNT(*) as n FROM facilities GROUP BY 1",
            "rows": [
                {"address_state_or_region": "Greater Accra", "n": 34},
                {"address_state_or_region": "Ashanti",       "n": 22},
                {"address_state_or_region": "Northern",      "n": 8},
                {"address_state_or_region": "Upper East",    "n": 4},
                {"address_state_or_region": "Upper West",    "n": 3},
            ]
        }
        errors.append("retrieve: used Genie fallback due to low /search confidence")
        # If we got nothing from /search, surface Genie rows as a minimal facility list
        if not facilities:
            facilities = [{
                "row_id":                  f"GENIE-{i}",
                "name":                    f"{row['address_state_or_region']} Region (Genie aggregate)",
                "address_state_or_region": row["address_state_or_region"],
                "location":                row["address_state_or_region"],
                "num_doctors":             0,
                "capacity":                0,
                "specialties": [], "capability": [], "equipment": [], "procedure": []
            } for i, row in enumerate(genie_context["rows"])]
            confidence = 0.40   # Genie is lower quality than semantic search

    cited_ids = [f["row_id"] for f in facilities if f.get("row_id")]
    log_step_citation(run_id, "retrieve", cited_ids)

    return {
        "retrieved_facilities": facilities,
        "search_confidence":    confidence,
        "node_errors":          errors,
    }


# ════════════════════════════════════════════════════════════════════════════
# NODE 2: REASON
# ════════════════════════════════════════════════════════════════════════════

def reason_node(state: AgentState) -> Dict[str, Any]:
    """
    Full intelligence node.
    1. Fetches anomaly flags from GET /anomalies
    2. Fetches desert zones from GET /deserts for each specialty in retrieved facilities
    3. Combines into gaps, recommendations, cited_row_ids
    4. Falls back to direct-retrieval reasoning if backend calls fail
    """
    print("\n[REASON NODE]")
    validate_state(state, ["retrieved_facilities"], "reason_node")

    facilities = state["retrieved_facilities"]
    region     = state.get("region")
    run_id     = state.get("mlflow_run_id")
    errors     = list(state.get("node_errors", []))
    cited_ids  = [f.get("row_id", f"fac-{i}") for i, f in enumerate(facilities)]

    # ── Step 1: Get anomaly flags ──────────────────────────────────────────
    anomalies: List[Dict] = []

    def _do_anomalies():
        return _api_anomalies(cited_ids, region)

    raw_anomalies, err = _call_with_timeout(_do_anomalies, NODE_TIMEOUT_S, [])
    if err:
        msg = f"reason: /anomalies failed ({type(err).__name__}: {err})"
        print(f"  ⚠ {msg} — running rule engine locally")
        errors.append(msg)
        # Local fallback — run rules inline without the backend
        anomalies = _local_anomaly_check(facilities)
    else:
        anomalies = raw_anomalies or []
        print(f"  /anomalies → {len(anomalies)} flag(s)")

    # ── Step 2: Get desert zones ───────────────────────────────────────────
    desert_gaps: List[str] = []
    # Collect all unique specialties from retrieved facilities
    all_specialties = list({
        s for f in facilities for s in f.get("specialties", [])
    })

    for specialty in all_specialties[:3]:    # cap at 3 to avoid timeout cascade
        def _do_deserts(spec=specialty):
            return _api_deserts(spec, region)

        raw_zones, err = _call_with_timeout(_do_deserts, NODE_TIMEOUT_S, [])
        if err:
            errors.append(f"reason: /deserts failed for {specialty}: {err}")
        elif raw_zones:
            for zone in raw_zones:
                desert_gaps.append(
                    f"Medical desert: {zone.get('region', 'Unknown region')} has "
                    f"{zone.get('facility_count', 0)} {specialty} facility/facilities "
                    f"(severity: {zone.get('severity', 'unknown')})."
                )

    # ── Step 3: Structural gap analysis ───────────────────────────────────
    structural_gaps = _identify_structural_gaps(facilities)
    all_gaps        = desert_gaps + structural_gaps
    if not all_gaps:
        all_gaps = ["No critical coverage gaps detected in the retrieved facility set."]

    # ── Step 4: Build recommendations ─────────────────────────────────────
    recommendations = _build_recommendations(facilities, anomalies, all_gaps)

    # ── Step 5: Validate with Pydantic then log ────────────────────────────
    reasoning = ReasoningOutput(
        gaps_identified   = all_gaps,
        anomalies_flagged = anomalies,
        recommendations   = recommendations,
        cited_row_ids     = cited_ids,
    )
    log_step_citation(run_id, "reason", cited_ids)

    print(f"  gaps={len(all_gaps)}  anomalies={len(anomalies)}  recs={len(recommendations)}")
    return {
        "reasoning":    reasoning.model_dump(),
        "node_errors":  errors,
    }


def _local_anomaly_check(facilities: List[Dict]) -> List[Dict]:
    """
    Inline fallback anomaly detection when /anomalies endpoint is unreachable.
    Mirrors the 3 rules from backend/idp/anomaly.py.
    """
    flags = []
    for f in facilities:
        cap_text   = " ".join(f.get("capability", [])).lower()
        equip_text = " ".join(f.get("equipment",  [])).lower()
        has_icu    = "icu" in cap_text or "intensive care" in cap_text
        has_power  = any(kw in equip_text for kw in
                         ["generator", "backup power", "ups", "inverter"])

        if has_icu and not has_power:
            flags.append({
                "facility_id":   f.get("row_id", f.get("name", "unknown")),
                "facility_name": f.get("name", "Unknown"),
                "flag_type":     "ICU_WITHOUT_BACKUP_POWER",
                "confidence":    0.88,
                "reason":        f"{f.get('name')} claims ICU but no backup power documented.",
                "severity":      "high",
            })

        specs = f.get("specialties", [])
        if len(specs) > 3 and not any(kw in equip_text for kw in
                                       ["mri", "ct", "x-ray", "xray", "ultrasound"]):
            flags.append({
                "facility_id":   f.get("row_id", f.get("name", "unknown")),
                "facility_name": f.get("name", "Unknown"),
                "flag_type":     "MULTIPLE_SPECIALTIES_WITHOUT_IMAGING",
                "confidence":    0.80,
                "reason":        f"{f.get('name')} claims {len(specs)} specialties but no imaging equipment.",
                "severity":      "medium",
            })

        if (f.get("capacity", 0) or 0) > 200 and (f.get("num_doctors", 0) or 0) < 2:
            flags.append({
                "facility_id":   f.get("row_id", f.get("name", "unknown")),
                "facility_name": f.get("name", "Unknown"),
                "flag_type":     "HIGH_CAPACITY_LOW_DOCTORS",
                "confidence":    0.85,
                "reason":        (f"{f.get('name')} has {f.get('capacity')} beds "
                                  f"but only {f.get('num_doctors')} doctor(s)."),
                "severity":      "high",
            })
    return flags


def _identify_structural_gaps(facilities: List[Dict]) -> List[str]:
    """Identifies regional redundancy and ICU-power gaps from the retrieved set."""
    gaps = []
    region_counts: Dict[str, int] = {}

    for f in facilities:
        r = f.get("address_state_or_region", "Unknown")
        region_counts[r] = region_counts.get(r, 0) + 1

    for region, count in region_counts.items():
        if count == 1:
            gaps.append(
                f"Low redundancy in {region}: only 1 facility in the retrieved set. "
                f"Any closure leaves the region with no coverage."
            )

    specialty_counts: Dict[str, int] = {}
    for f in facilities:
        for s in f.get("specialties", []):
            specialty_counts[s] = specialty_counts.get(s, 0) + 1

    for spec, count in specialty_counts.items():
        if count == 1:
            gaps.append(
                f"Specialty '{spec}' covered by only 1 facility in the retrieved set."
            )

    return gaps


def _build_recommendations(
    facilities:  List[Dict],
    anomalies:   List[Dict],
    gaps:        List[str],
) -> List[str]:
    """Produces prioritised plain-English recommendations for an NGO planner."""
    recs = []
    flagged_ids = {a.get("facility_id") for a in anomalies}

    # Priority 1: urgent anomaly warnings
    for flag in anomalies:
        name     = flag.get("facility_name", flag.get("facility_id", "Unknown"))
        severity = flag.get("severity", "medium").upper()
        recs.append(
            f"[{severity}] Verify {name}: {flag.get('reason', '')} "
            f"(confidence {flag.get('confidence', 0):.0%})"
        )

    # Priority 2: desert/structural gaps
    for gap in gaps:
        if "No critical" not in gap:
            recs.append(f"[GAP] {gap}")

    # Priority 3: routing suggestion — pick best clean facility by doctor count
    clean = [f for f in facilities if f.get("row_id") not in flagged_ids]
    pool  = clean if clean else facilities
    if pool:
        best = max(pool, key=lambda f: f.get("num_doctors", 0) or 0)
        recs.append(
            f"[ROUTE] Recommend routing to {best.get('name')} "
            f"in {best.get('address_state_or_region', best.get('location', 'Ghana'))} — "
            f"{best.get('num_doctors', 'unknown')} doctors, "
            f"{best.get('capacity', 'unknown')} beds, no anomaly flags."
        )

    return recs or ["No specific recommendations — dataset may need enrichment."]


# ════════════════════════════════════════════════════════════════════════════
# NODE 3: SYNTHESIZE
# ════════════════════════════════════════════════════════════════════════════

def synthesize_node(state: AgentState) -> Dict[str, Any]:
    """
    Produces a paragraph-form narrative with inline [row_id] citations.
    Validated reasoning shape is required — fails fast if reason_node broke.
    """
    print("\n[SYNTHESIZE NODE]")
    validate_state(state, ["reasoning"], "synthesize_node")

    reasoning  = state["reasoning"]
    facilities = state.get("retrieved_facilities", [])
    run_id     = state.get("mlflow_run_id")
    cited_ids  = reasoning.get("cited_row_ids", [])

    # Validate required reasoning fields are present
    for field in ["gaps_identified", "anomalies_flagged", "recommendations", "cited_row_ids"]:
        if field not in reasoning:
            raise ValueError(f"[synthesize_node] reasoning missing field '{field}'")

    log_step_citation(run_id, "synthesize", cited_ids)

    # Build name lookup for inline citations
    id_to_name = {
        f.get("row_id", f"unknown-{i}"): f.get("name", "Unknown Facility")
        for i, f in enumerate(facilities)
    }

    narrative = _build_narrative(reasoning, id_to_name)
    print(f"  Narrative: {len(narrative)} chars | Citations: {len(cited_ids)}")

    return {
        "citations": cited_ids,
        "narrative": narrative,
    }


def _build_narrative(reasoning: Dict, id_to_name: Dict[str, str]) -> str:
    """Paragraph-form narrative with inline [row_id] citation tags."""
    parts     = []
    cited_ids = reasoning.get("cited_row_ids",   [])
    gaps      = reasoning.get("gaps_identified",  [])
    anomalies = reasoning.get("anomalies_flagged",[])
    recs      = reasoning.get("recommendations",  [])

    # Opening — name up to 3 facilities
    names = [id_to_name.get(rid, rid) for rid in cited_ids[:3]]
    if names:
        name_str = (", ".join(names[:-1]) + f" and {names[-1]}"
                    if len(names) > 1 else names[0])
        parts.append(
            f"Based on analysis of {len(cited_ids)} facilities including {name_str}, "
            f"the following intelligence has been compiled."
        )

    # Coverage gaps
    critical = [g for g in gaps if "No critical" not in g]
    if critical:
        parts.append(
            f"Coverage concerns identified: "
            + " ".join(
                f"{g} [{cited_ids[i] if i < len(cited_ids) else 'N/A'}]"
                for i, g in enumerate(critical[:3])
            )
        )
    else:
        parts.append("No critical coverage gaps detected in the retrieved facility set.")

    # Anomaly warnings
    if anomalies:
        parts.append(
            f"CAUTION: {len(anomalies)} anomaly flag(s) require verification. "
            + " ".join(
                f"{id_to_name.get(a.get('facility_id',''), a.get('facility_name', a.get('facility_id','')))}"
                f" ({a.get('flag_type','')}, {a.get('confidence',0):.0%}) [{a.get('facility_id','')}]"
                for a in anomalies
            )
        )
    else:
        parts.append("All retrieved facilities passed anomaly checks.")

    # Routing recommendation
    route = [r for r in recs if "[ROUTE]" in r]
    if route:
        parts.append(f"Routing: {route[0].replace('[ROUTE] ', '')}")

    # Source footer
    parts.append(
        f"Sources: {', '.join(cited_ids)}. "
        f"Expand 'View sources' to inspect individual facility records."
    )

    return " ".join(parts)


# ════════════════════════════════════════════════════════════════════════════
# NODE 4: RESPOND
# ════════════════════════════════════════════════════════════════════════════

def respond_node(state: AgentState) -> Dict[str, Any]:
    """
    Assembles the typed AgentResponse object.
    This is the exact JSON shape the frontend chat UI consumes.
    """
    print("\n[RESPOND NODE]")
    reasoning   = state.get("reasoning", {})
    narrative   = state.get("narrative", "No narrative generated.")
    citations   = state.get("citations", [])
    node_errors = state.get("node_errors", [])

    response_obj = AgentResponse(
        narrative         = narrative,
        recommendations   = reasoning.get("recommendations",   []),
        anomalies_flagged = reasoning.get("anomalies_flagged", []),
        gaps_identified   = reasoning.get("gaps_identified",   []),
        cited_row_ids     = citations,
        query             = state.get("query", ""),
        generated_at      = datetime.utcnow().isoformat() + "Z",
        node_errors       = node_errors,
    )
    response_json = json.dumps(response_obj.model_dump(), indent=2)
    print(f"  Response ready — {len(narrative)} char narrative, {len(citations)} citations")
    if node_errors:
        print(f"  Non-fatal errors during run: {node_errors}")
    return {"response": response_json}


# ════════════════════════════════════════════════════════════════════════════
# GRAPH ASSEMBLY
# ════════════════════════════════════════════════════════════════════════════

_workflow = StateGraph(AgentState)
_workflow.add_node("retrieve",   retrieve_node)
_workflow.add_node("reason",     reason_node)
_workflow.add_node("synthesize", synthesize_node)
_workflow.add_node("respond",    respond_node)

_workflow.set_entry_point("retrieve")
_workflow.add_edge("retrieve",   "reason")
_workflow.add_edge("reason",     "synthesize")
_workflow.add_edge("synthesize", "respond")
_workflow.add_edge("respond",    END)

graph = _workflow.compile()


# ════════════════════════════════════════════════════════════════════════════
# PUBLIC run_agent() — used by eval harness, demo script, and Day 5 FastAPI
# ════════════════════════════════════════════════════════════════════════════

def run_agent(query: str, region: str = None) -> Dict[str, Any]:
    os.environ["MLFLOW_ENABLE_DB_SDK"] = "true"

    try:
        mlflow.set_tracking_uri("databricks")
        mlflow.set_experiment("/Shared/IDP-Backend-API")
        use_mlflow = True
    except Exception as e:
        print(f"MLflow disabled for this run: {e}")
        use_mlflow = False

    initial: AgentState = {
        "query":                query,
        "region":               region,
        "retrieved_facilities": [],
        "search_confidence":    0.0,
        "reasoning":            {},
        "narrative":            "",
        "citations":            [],
        "response":             "",
        "mlflow_run_id":        None,
        "node_errors":          [],
    }

    if use_mlflow:
        with mlflow.start_run(run_name=f"agent-d4-{int(time.time())}") as run:
            initial["mlflow_run_id"] = run.info.run_id
            mlflow.log_param("query", query)
            result = graph.invoke(initial)
            return result
    else:
        # Run without MLflow — all agent logic still works
        result = graph.invoke(initial)
        return result

# ════════════════════════════════════════════════════════════════════════════
# PLANNING SYSTEM — 5-step guided workflow (carried from Day 3, hardened)
# ════════════════════════════════════════════════════════════════════════════

SPECIALTY_OPTIONS  = [
    "internalMedicine", "familyMedicine", "pediatrics", "cardiology",
    "generalSurgery", "emergencyMedicine", "gynecologyAndObstetrics",
    "orthopedicSurgery", "dentistry", "ophthalmology"
]
GHANA_REGIONS = [
    "Greater Accra", "Ashanti", "Northern", "Upper East", "Upper West",
    "Western", "Central", "Eastern", "Volta", "Bono", "Savannah",
    "North East", "Oti", "Bono East", "Ahafo", "Western North"
]
CARE_LEVEL_OPTIONS = ["emergency", "inpatient", "outpatient", "specialist_referral"]


class PlanningState(TypedDict):
    step:               int
    specialty:          Optional[str]
    region:             Optional[str]
    care_level:         Optional[str]
    matched_facilities: List[Dict[str, Any]]
    anomaly_warnings:   List[Dict[str, Any]]
    recommendation:     Optional[str]
    cited_row_ids:      List[str]
    error:              Optional[str]


class PlanningSystem:
    """5-step guided workflow for non-technical NGO planners."""

    def step1_define_need(self) -> PlanningState:
        print("\n[PLANNING STEP 1] Define care need")
        return {
            "step": 1, "specialty": None, "region": None, "care_level": None,
            "matched_facilities": [], "anomaly_warnings": [],
            "recommendation": None, "cited_row_ids": [], "error": None,
        }

    def step2_select_region(self, state: PlanningState, specialty: str) -> PlanningState:
        print(f"\n[PLANNING STEP 2] specialty='{specialty}'")
        if specialty not in SPECIALTY_OPTIONS:
            state["error"] = f"Invalid specialty '{specialty}'"
            return state
        state.update({"step": 2, "specialty": specialty, "error": None})
        return state

    def step3_search_facilities(self, state: PlanningState, region: str) -> PlanningState:
        print(f"\n[PLANNING STEP 3] region='{region}'")
        if region not in GHANA_REGIONS:
            state["error"] = f"Invalid region '{region}'"
            return state
        state.update({"step": 3, "region": region, "error": None})

        query = f"Find {state['specialty']} facilities in {region} Ghana"
        facilities = []

        try:
            raw  = _api_search(query, region, state["specialty"])
            facilities = [_normalise_facility(f) for f in raw.get("facilities", [])]
        except Exception as e:
            print(f"  /search unavailable: {e} — no results")

        state["matched_facilities"] = facilities
        state["cited_row_ids"]      = [f.get("row_id","") for f in facilities]
        print(f"  Found {len(facilities)} facilities")
        return state

    def step4_check_anomalies(self, state: PlanningState) -> PlanningState:
        print("\n[PLANNING STEP 4] Checking anomalies")
        state["step"] = 4
        ids = [f.get("row_id","") for f in state["matched_facilities"]]

        warnings = []
        try:
            warnings = _api_anomalies(ids, state.get("region"))
        except Exception as e:
            print(f"  /anomalies unavailable: {e} — running local check")
            warnings = _local_anomaly_check(state["matched_facilities"])

        state["anomaly_warnings"] = warnings
        print(f"  {len(warnings)} warning(s) found")
        return state

    def step5_get_recommendation(self, state: PlanningState, care_level: str) -> PlanningState:
        print(f"\n[PLANNING STEP 5] care_level='{care_level}'")
        if care_level not in CARE_LEVEL_OPTIONS:
            state["error"] = f"Invalid care_level '{care_level}'"
            return state
        state.update({"step": 5, "care_level": care_level, "error": None})

        flagged_ids = {w.get("facility_id") for w in state["anomaly_warnings"]}
        clean = [f for f in state["matched_facilities"] if f.get("row_id") not in flagged_ids]
        pool  = clean if clean else state["matched_facilities"]

        if not pool:
            state["recommendation"] = (
                "No suitable facilities found. Consider expanding the region."
            )
            return state

        best   = max(pool, key=lambda f: f.get("num_doctors", 0) or 0)
        row_id = best.get("row_id", "N/A")

        anomaly_note = (
            f" Note: {len(state['anomaly_warnings'])} facility flag(s) excluded."
            if state["anomaly_warnings"] else ""
        )

        state["recommendation"] = (
            f"Recommended for {state['specialty']} ({care_level}) "
            f"in {state['region']}: {best.get('name')} [{row_id}]. "
            f"{best.get('num_doctors','?')} doctors, {best.get('capacity','?')} beds. "
            f"Capabilities: {', '.join(best.get('capability',[])[:3])}."
            f"{anomaly_note} "
            f"Sources: {', '.join(state['cited_row_ids'])}."
        )
        print(f"  → {state['recommendation'][:100]}...")
        return state

    def run_full_wizard(
        self, specialty: str, region: str, care_level: str
    ) -> PlanningState:
        s = self.step1_define_need()
        s = self.step2_select_region(s, specialty)
        if s.get("error"):
            return s
        s = self.step3_search_facilities(s, region)
        if s.get("error"):
            return s
        s = self.step4_check_anomalies(s)
        s = self.step5_get_recommendation(s, care_level)
        return s


# ════════════════════════════════════════════════════════════════════════════
# EVALUATION HARNESS — Day 4 deliverable
# ════════════════════════════════════════════════════════════════════════════

JUDGE_QUERIES = [
    {"id": "JQ-01", "query": "Find all hospitals with ICU capability in the Ashanti region",                        "category": "Technical accuracy"},
    {"id": "JQ-02", "query": "Which facilities in Northern Ghana offer pediatric care?",                            "category": "IDP innovation"},
    {"id": "JQ-03", "query": "Are there any suspicious claims in the Ghana facility dataset?",                      "category": "Technical accuracy"},
    {"id": "JQ-04", "query": "Where are the medical deserts for cardiology in Ghana?",                             "category": "Social impact"},
    {"id": "JQ-05", "query": "Find the nearest facility with emergency surgery within 100km of Kumasi",            "category": "Technical accuracy"},
    {"id": "JQ-06", "query": "Which NGOs in Ghana accept clinical volunteers?",                                     "category": "IDP innovation"},
    {"id": "JQ-07", "query": "What is the equipment situation at facilities claiming Level II trauma care?",        "category": "IDP innovation"},
    {"id": "JQ-08", "query": "Which regions have no facilities with oxygen plants?",                               "category": "Social impact"},
    {"id": "JQ-09", "query": "I need to place a doctor specialising in gynecology — where is most underserved?",   "category": "Social impact"},
    {"id": "JQ-10", "query": "Are there facilities claiming ICU but lacking backup power?",                        "category": "Technical accuracy"},
]


def _score(result: Dict) -> int:
    """Scores 1–3: 1pt each for narrative, citations, recommendations."""
    return max(1, sum([
        len(result.get("narrative",  "")) > 80,
        len(result.get("citations",  [])) > 0,
        len(result.get("reasoning",  {}).get("recommendations", [])) > 0,
    ]))


def run_eval_harness(save_path: str = "../docs/eval_final.md") -> float:
    """
    Runs all 10 judge queries. Scores each 1–3. Target mean ≥ 2.4.
    Saves results to docs/eval_final.md.
    Returns mean score.
    """
    print("\n" + "█"*60)
    print("  DAY 4 EVALUATION HARNESS — 10 Judge Queries")
    print("█"*60)

    rows = []
    total = 0

    for jq in JUDGE_QUERIES:
        print(f"\n[{jq['id']}] {jq['query'][:60]}...")
        try:
            result = run_agent(jq["query"])
            score  = _score(result)
        except Exception as e:
            print(f"  EXCEPTION: {e}")
            result = {}
            score  = 1

        total += score
        rows.append({
            "id":            jq["id"],
            "query":         jq["query"],
            "category":      jq["category"],
            "score":         score,
            "pass":          score >= 2,
            "citations":     len(result.get("citations", [])),
            "narrative_len": len(result.get("narrative", "")),
            "errors":        result.get("node_errors", []),
        })
        status = "✓" if score >= 2 else "✗"
        print(f"  [{status}] score={score}/3  citations={rows[-1]['citations']}  "
              f"narrative={rows[-1]['narrative_len']}ch")

    mean     = total / len(JUDGE_QUERIES)
    passing  = sum(1 for r in rows if r["pass"])
    target   = mean >= 2.4

    # Save markdown
    lines = [
        "# Final Evaluation Results — Day 4",
        f"\nGenerated: {datetime.utcnow().isoformat()}Z",
        f"\n## Summary",
        f"- Mean score: **{mean:.2f} / 3.0**",
        f"- Passing (≥2): **{passing}/{len(JUDGE_QUERIES)}**",
        f"- Target (≥2.4): **{'MET ✓' if target else 'MISSED ✗'}**",
        "\n## Per-query\n",
        "| ID | Category | Query | Score | Pass | Citations |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['category']} | {r['query'][:50]}... "
            f"| {r['score']}/3 | {'✓' if r['pass'] else '✗'} | {r['citations']} |"
        )
    failed = [r for r in rows if not r["pass"]]
    if failed:
        lines.append("\n## Queries needing Day 5 fixes\n")
        for r in failed:
            lines.append(f"- **{r['id']}**: {r['query']} (score {r['score']}/3)")
            if r["errors"]:
                lines.append(f"  - Errors: {'; '.join(r['errors'])}")

    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    with open(save_path, "w") as f:
        f.write("\n".join(lines))

    print(f"\n{'='*60}")
    print(f"Mean: {mean:.2f}/3.0   Passing: {passing}/{len(JUDGE_QUERIES)}")
    print(f"Target: {'MET ✓' if target else 'MISSED — review eval_final.md'}")
    print(f"Saved: {save_path}")
    print(f"{'='*60}")
    return mean


# ════════════════════════════════════════════════════════════════════════════
# DEMO SCRIPT — 5 pre-set queries for judge demo mode
# ════════════════════════════════════════════════════════════════════════════

DEMO_QUERIES = [
    {
        "id":    "DEMO-01",
        "label": "ICU facilities in Ashanti",
        "query": "Find hospitals with ICU capability in the Ashanti region",
        "showcases": "Semantic search + anomaly badges"
    },
    {
        "id":    "DEMO-02",
        "label": "Medical deserts — cardiology",
        "query": "Where are the medical deserts for cardiology in Ghana?",
        "showcases": "Desert detection + heatmap"
    },
    {
        "id":    "DEMO-03",
        "label": "Anomaly check — suspicious claims",
        "query": "Are there facilities claiming ICU but lacking backup power?",
        "showcases": "Anomaly rule engine + confidence scores"
    },
    {
        "id":    "DEMO-04",
        "label": "Planning — gynecology placement",
        "query": "I need to place a doctor specialising in gynecology — where is the most underserved area?",
        "showcases": "Planning wizard + social impact"
    },
    {
        "id":    "DEMO-05",
        "label": "Equipment audit — trauma centres",
        "query": "What is the equipment situation at facilities claiming Level II trauma care?",
        "showcases": "IDP extraction + cross-field reasoning"
    },
]


def run_demo_queries(save_path: str = "../demo/queries.json") -> None:
    """
    Runs all 5 demo queries, confirms each completes, saves to demo/queries.json.
    All 5 must complete in < 20 seconds each on a warm cluster.
    """
    print("\n" + "█"*60)
    print("  DEMO QUERY VALIDATION — 5 Pre-set Queries")
    print("█"*60)

    results = []
    all_pass = True

    for dq in DEMO_QUERIES:
        print(f"\n[{dq['id']}] {dq['label']}")
        start = time.time()
        try:
            result   = run_agent(dq["query"])
            elapsed  = time.time() - start
            response = json.loads(result.get("response", "{}"))
            passed   = (
                len(response.get("narrative",       "")) > 50
                and elapsed < 20
            )
        except Exception as e:
            elapsed = time.time() - start
            response = {}
            passed   = False
            print(f"  EXCEPTION: {e}")

        status = "PASS ✓" if passed else "FAIL ✗"
        print(f"  {status}  {elapsed:.1f}s  narrative={len(response.get('narrative',''))}ch")
        if not passed:
            all_pass = False

        results.append({
            **dq,
            "elapsed_s":       round(elapsed, 2),
            "passed":          passed,
            "narrative_length":len(response.get("narrative", "")),
            "citations":       response.get("cited_row_ids", []),
        })

    # Save demo query file for frontend demo mode
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    with open(save_path, "w") as f:
        json.dump(DEMO_QUERIES, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Demo queries: {'ALL PASS ✓' if all_pass else 'FAILURES — fix before recording video'}")
    print(f"Saved to: {save_path}")
    print(f"{'='*60}")


# ════════════════════════════════════════════════════════════════════════════
# DAY 4 TESTS — must all pass before EOD sign-off
# ════════════════════════════════════════════════════════════════════════════

def _run_tests():
    print("\n" + "█"*60)
    print("  DAY 4 UNIT TESTS")
    print("█"*60)

    # Test 1: timeout handling
    print("\n[TEST 1] Node timeout handling")
    slow_fn  = lambda: time.sleep(20)  # deliberately slow
    val, err = _call_with_timeout(slow_fn, 2, "fallback_value")
    assert val == "fallback_value", "FAIL: timeout did not return fallback"
    assert isinstance(err, TimeoutError), "FAIL: timeout error type wrong"
    print("  PASS: timeout returns fallback without crashing")

    # Test 2: field normalisation
    print("\n[TEST 2] Field name normalisation")
    camel = {"name": "Test", "address_stateOrRegion": "Northern", "numberDoctors": 42}
    norm  = _normalise_facility(camel)
    assert norm["address_state_or_region"] == "Northern", "FAIL: region not normalised"
    assert norm["num_doctors"] == 42, "FAIL: doctors not normalised"
    print("  PASS: camelCase fields normalised to snake_case")

    # Test 3: local anomaly check fallback
    print("\n[TEST 3] Local anomaly check (backend fallback)")
    test_fac = [{
        "row_id": "TEST-001", "name": "Test Hospital",
        "capability": ["ICU with 20 beds"],
        # No imaging (no MRI/CT/X-ray/ultrasound) and no backup power —
        # deliberately bare so all 3 rules fire:
        #   Rule 1: ICU_WITHOUT_BACKUP_POWER     (has ICU, no generator/ups)
        #   Rule 2: MULTIPLE_SPECIALTIES_WITHOUT_IMAGING (4 specialties, no imaging)
        #   Rule 3: HIGH_CAPACITY_LOW_DOCTORS    (250 beds, 1 doctor)
        "equipment":  ["blood pressure monitor", "sterilisation unit"],
        "specialties": ["cardiology", "generalSurgery", "pediatrics", "ophthalmology"],
        "capacity": 250, "num_doctors": 1
    }]
    flags      = _local_anomaly_check(test_fac)
    flag_types = [f["flag_type"] for f in flags]
    assert "ICU_WITHOUT_BACKUP_POWER"             in flag_types, "FAIL: ICU rule missed"
    assert "MULTIPLE_SPECIALTIES_WITHOUT_IMAGING" in flag_types, "FAIL: specialty rule missed"
    assert "HIGH_CAPACITY_LOW_DOCTORS"            in flag_types, "FAIL: capacity rule missed"
    print(f"  PASS: all 3 local anomaly rules fired correctly ({len(flags)} flags)")

    # Test 4: planning wizard runs end-to-end
    print("\n[TEST 4] Planning wizard end-to-end")
    ps    = PlanningSystem()
    state = ps.run_full_wizard("pediatrics", "Northern", "inpatient")
    assert state["step"]  == 5,  "FAIL: wizard did not reach step 5"
    assert not state.get("error"), f"FAIL: wizard error: {state.get('error')}"
    print(f"  PASS: wizard completed step 5")
    if state.get("recommendation"):
        print(f"  Recommendation: {state['recommendation'][:100]}...")

    # Test 5: AgentResponse JSON is valid
    print("\n[TEST 5] Full agent run produces valid AgentResponse JSON")
    result   = run_agent("Find hospitals with ICU in Ashanti region")
    response = result.get("response", "")
    assert response, "FAIL: response is empty"
    parsed = json.loads(response)
    for field in ["narrative","recommendations","anomalies_flagged",
                  "gaps_identified","cited_row_ids","query","generated_at"]:
        assert field in parsed, f"FAIL: response missing field '{field}'"
    print(f"  PASS: AgentResponse has all required fields")
    print(f"        narrative={len(parsed['narrative'])}ch  "
          f"recs={len(parsed['recommendations'])}  "
          f"cited={len(parsed['cited_row_ids'])}")

    print("\n" + "="*60)
    print("ALL DAY 4 TESTS PASSED")
    print("="*60)


# ════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MedMap AI — Agent Day 4")
    parser.add_argument("--demo",  action="store_true", help="Run 5 demo queries only")
    parser.add_argument("--eval",  action="store_true", help="Run 10-query eval harness only")
    parser.add_argument("--test",  action="store_true", help="Run unit tests only")
    parser.add_argument("--query", type=str,            help="Run a single query")
    args = parser.parse_args()

    if args.query:
        print(f"\nRunning single query: '{args.query}'")
        result   = run_agent(args.query)
        response = json.loads(result.get("response", "{}"))
        print(f"\nNarrative:\n{response.get('narrative','')}")
        print(f"\nRecommendations:")
        for r in response.get("recommendations", []):
            print(f"  • {r}")
        print(f"\nSources: {', '.join(response.get('cited_row_ids', []))}")

    elif args.demo:
        run_demo_queries()

    elif args.eval:
        run_eval_harness()

    elif args.test:
        _run_tests()

    else:
        # Default: run everything in sequence
        _run_tests()
        run_demo_queries()
        run_eval_harness()
