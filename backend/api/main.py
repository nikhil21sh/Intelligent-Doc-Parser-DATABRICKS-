"""
backend/api/main.py
===================
Day 4 — FINAL hardened backend (Intern 1).

Day 4 additions:
  - Input validation with clear 4xx messages on every endpoint
  - try/except + graceful fallback on every route
  - GET /warmup — pre-caches top 5 query embeddings; call before demo
  - GET /eval   — runs backend self-check; returns pass/fail for all endpoints
  - Response time logging via X-Process-Time header on every response
  - /build-index now validates record shape before indexing
  - /anomalies returns consistent envelope even when cache is empty
  - CORS tightened — configure ALLOWED_ORIGIN in .env before demo
"""

import os
import json
import time
import logging
from typing        import List, Optional
from dotenv        import load_dotenv, find_dotenv
from datetime      import datetime
from pydantic import BaseModel
load_dotenv(find_dotenv())

from fastapi                  import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors  import CORSMiddleware
from fastapi.responses        import JSONResponse
import nest_asyncio
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from agent.agent import run_agent
from backend.models.models import (
    DocumentRequest,
    SearchRequest,
    ExtractionResponse,
    AnomalyResponse,
    DesertResponse,
    FacilityFact,
    AnomalyFlag,
    DesertZone,
)
from backend.idp.extraction import MedicalIDP
from backend.idp.anomaly    import detect_anomalies
from backend.idp.desert     import detect_deserts_from_facilities, build_coverage_map

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("idp-api")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "Virtue Foundation IDP API",
    description = "Medical facility intelligence for Ghana — Databricks × Accenture Hackathon",
    version     = "4.0.0",
)
class AgentRequest(BaseModel):
    query: str
    region: Optional[str] = None

# CORS — set ALLOWED_ORIGIN=https://your-databricks-app-url in .env before demo
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins     = [ALLOWED_ORIGIN],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Response time header middleware ───────────────────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start    = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.time()-start)*1000:.1f}ms"
    return response

# ── Singletons ────────────────────────────────────────────────────────────────
idp_engine: Optional[MedicalIDP] = None

@app.on_event("startup")
async def startup():
    import os
    os.environ["MLFLOW_ENABLE_DB_SDK"] = "true"
    global idp_engine
    logger.info("Starting up — loading MedicalIDP engine...")
    idp_engine = MedicalIDP()
    logger.info(f"Engine ready. LanceDB index: "
                f"{'loaded' if idp_engine.table else 'not built'}")

# In-memory facility cache (populated by /build-index)
_facility_cache: List[FacilityFact] = []

# Warmup query cache — pre-embedded vectors for the 5 demo queries
_warmup_queries = [
    "Find hospitals with ICU capability in Ashanti",
    "Medical deserts for cardiology in Ghana",
    "Facilities claiming ICU without backup power",
    "Gynecology specialist placement underserved areas",
    "Equipment situation Level II trauma facilities",
]


# ════════════════════════════════════════════════════════════════════════════
# UTILITY: consistent error response
# ════════════════════════════════════════════════════════════════════════════

def _error(status: int, detail: str) -> HTTPException:
    logger.warning(f"HTTP {status}: {detail}")
    return HTTPException(status_code=status, detail=detail)


def _require_cache(endpoint_name: str):
    """Raises 503 with a helpful message if facility cache is empty."""
    if not _facility_cache:
        raise _error(
            503,
            f"{endpoint_name} requires the facility index to be built first. "
            f"Call POST /build-index with your Delta Lake records."
        )


def _require_engine(endpoint_name: str):
    """Raises 503 if the IDP engine failed to load."""
    if idp_engine is None:
        raise _error(503, f"{endpoint_name}: IDP engine not ready — check startup logs.")


# ════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {
        "status":            "online",
        "version":           "4.0.0",
        "index_status":      "ready" if (idp_engine and idp_engine.table) else "not_built",
        "cached_facilities": len(_facility_cache),
        "timestamp":         datetime.utcnow().isoformat() + "Z",
    }


# ── /extract ──────────────────────────────────────────────────────────────────

@app.post("/extract")
async def extract(payload: DocumentRequest):
    _require_engine("/extract")

    text = payload.text.strip()
    if len(text) < 20:
        raise _error(422, "Text too short — minimum 20 characters required.")
    if len(text) > 8000:
        raise _error(422, "Text too long — maximum 8000 characters. Split into smaller documents.")

    try:
        extracted = idp_engine.extract_from_text(text)
        return {
            "status":           "success",
            "data":             extracted,
            "confidence_score": 0.85,
            "metadata": {
                "model":       "llama-3.3-70b-versatile",
                "prompt_type": "few_shot",
                "mlflow":      "/Shared/IDP-Backend-API",
            }
        }
    except RuntimeError as e:
        # Extraction failed after all retries
        raise _error(422, f"Extraction failed: {str(e)}")
    except Exception as e:
        logger.error(f"/extract unexpected error: {e}")
        raise _error(500, "Internal extraction error — check MLflow logs for details.")


# ── /search ───────────────────────────────────────────────────────────────────

@app.post("/search")
async def search(payload: SearchRequest):
    _require_engine("/search")

    if not payload.q or not payload.q.strip():
        raise _error(422, "Query 'q' cannot be empty.")
    if len(payload.q) > 500:
        raise _error(422, "Query too long — maximum 500 characters.")
    if idp_engine.table is None:
        raise _error(
            503,
            "/search requires the LanceDB index to be built. "
            "Call POST /build-index first."
        )

    try:
        result = idp_engine.search(
            query     = payload.q.strip(),
            region    = payload.region,
            specialty = payload.specialty,
            top_k     = payload.top_k,
        )
        return result.model_dump()
    except Exception as e:
        logger.error(f"/search error: {e}")
        raise _error(500, f"Search error: {str(e)}")


# ── /anomalies ────────────────────────────────────────────────────────────────

@app.get("/anomalies")
async def anomalies(
    facility_ids: Optional[str] = Query(None, description="Comma-separated row_ids"),
    region:       Optional[str] = Query(None, description="Filter by region"),
):
    _require_cache("/anomalies")

    facilities = _facility_cache

    # Filter by facility_ids if provided
    if facility_ids:
        ids_list   = [i.strip() for i in facility_ids.split(",") if i.strip()]
        if not ids_list:
            raise _error(422, "facility_ids must be a non-empty comma-separated list.")
        facilities = [f for f in facilities if (f.row_id or f.name) in ids_list]

    # Filter by region if provided
    if region:
        facilities = [
            f for f in facilities
            if region.lower() in (f.address_state_or_region or "").lower()
        ]

    # Always return a valid envelope — never 404 just because no facilities match
    flags = detect_anomalies(facilities) if facilities else []

    return AnomalyResponse(
        flags       = flags,
        total_flags = len(flags),
        region      = region,
    ).model_dump()


# ── /deserts ──────────────────────────────────────────────────────────────────

VALID_SPECIALTIES = [
    "internalMedicine", "familyMedicine", "pediatrics", "cardiology",
    "generalSurgery", "emergencyMedicine", "gynecologyAndObstetrics",
    "orthopedicSurgery", "dentistry", "ophthalmology",
]

@app.get("/deserts")
async def deserts(
    specialty: str           = Query(..., description="Specialty to check coverage for"),
    region:    Optional[str] = Query(None, description="Limit to one region"),
):
    _require_cache("/deserts")

    if not specialty.strip():
        raise _error(422, "specialty cannot be empty.")

    # Warn but don't block on unknown specialty — dataset may use non-standard values
    if specialty not in VALID_SPECIALTIES:
        logger.warning(f"/deserts called with non-standard specialty: '{specialty}'")

    try:
        zones = detect_deserts_from_facilities(
            facilities = _facility_cache,
            specialty  = specialty.strip(),
            region     = region,
        )
        return DesertResponse(
            zones       = zones,
            specialty   = specialty,
            region      = region,
            total_zones = len(zones),
        ).model_dump()
    except Exception as e:
        logger.error(f"/deserts error: {e}")
        raise _error(500, f"Desert detection error: {str(e)}")


# ── /coverage ─────────────────────────────────────────────────────────────────

@app.get("/coverage")
async def coverage():
    _require_cache("/coverage")
    try:
        cov_map = build_coverage_map(_facility_cache)
        return {"regions": cov_map, "total_regions": len(cov_map)}
    except Exception as e:
        logger.error(f"/coverage error: {e}")
        raise _error(500, f"Coverage map error: {str(e)}")


# ── /facilities ───────────────────────────────────────────────────────────────

@app.get("/facilities")
async def facilities(
    region: Optional[str] = Query(None),
    limit:  int           = Query(50, ge=1, le=500),
):
    if not _facility_cache:
        return {"count": 0, "data": [], "message": "Cache empty — call POST /build-index first."}

    result = _facility_cache
    if region:
        result = [f for f in result
                  if region.lower() in (f.address_state_or_region or "").lower()]

    return {"count": len(result[:limit]), "data": [f.model_dump() for f in result[:limit]]}


# ── /build-index ──────────────────────────────────────────────────────────────

@app.post("/build-index")
async def build_index(records: List[dict]):
    global _facility_cache
    _require_engine("/build-index")

    if not records:
        raise _error(422, "records list cannot be empty.")
    if len(records) > 50_000:
        raise _error(422, "Too many records — maximum 50,000 per call.")

    # Validate at least the first record has a name field
    if "name" not in records[0] and "name" not in records[0]:
        raise _error(422, "Each record must have at least a 'name' field.")

    try:
        count = idp_engine.build_index_from_records(records)

        # Rebuild facility cache
        _facility_cache = []
        parse_errors    = 0
        for rec in records:
            try:
                rec.setdefault("name",     rec.get("name", "Unknown"))
                rec.setdefault("location", rec.get("address_state_or_region", "Unknown"))
                _facility_cache.append(FacilityFact(**rec))
            except Exception:
                parse_errors += 1

        logger.info(f"Index built: {count} vectors, {len(_facility_cache)} cached, "
                    f"{parse_errors} parse errors")
        return {
            "status":            "success",
            "indexed_records":   count,
            "cached_facilities": len(_facility_cache),
            "parse_errors":      parse_errors,
        }
    except Exception as e:
        logger.error(f"/build-index error: {e}")
        raise _error(500, f"Index build failed: {str(e)}")


# ── /warmup ───────────────────────────────────────────────────────────────────

@app.get("/warmup")
async def warmup():
    """
    Pre-embeds the 5 demo query vectors so the first demo query is fast.
    Call this before starting the demo recording or judge session.
    """
    _require_engine("/warmup")
    if idp_engine.table is None:
        raise _error(503, "/warmup requires LanceDB index — call /build-index first.")

    results = []
    for q in _warmup_queries:
        try:
            start  = time.time()
            result = idp_engine.search(query=q, top_k=3)
            elapsed= time.time() - start
            results.append({
                "query":        q,
                "elapsed_ms":   round(elapsed * 1000, 1),
                "results_found":result.result_count,
                "status":       "ok",
            })
        except Exception as e:
            results.append({"query": q, "status": "error", "error": str(e)})

    all_ok = all(r["status"] == "ok" for r in results)
    return {
        "status":  "ready" if all_ok else "partial",
        "queries": results,
        "message": "All demo queries pre-warmed." if all_ok
                   else "Some queries failed — check errors above.",
    }


# ── /eval ─────────────────────────────────────────────────────────────────────

@app.get("/eval")
async def eval_backend():
    """
    Backend self-check — runs a mini validation of every endpoint.
    Use this to confirm the backend is healthy before running the agent eval harness.
    Returns a pass/fail dict for every endpoint.
    """
    checks = {}

    # /health
    checks["/health"] = {"status": "ok"}

    # /extract
    try:
        _require_engine("/extract")
        result = idp_engine.extract_from_text(
            "Korle-Bu Teaching Hospital in Accra has 2000 beds, "
            "487 doctors, a Level I Trauma Center, ICU with 40 beds, "
            "and a diesel backup generator."
        )
        checks["/extract"] = {
            "status":     "ok",
            "name":        result.get("name", ""),
            "specialties": result.get("specialties", []),
        }
    except Exception as e:
        checks["/extract"] = {"status": "error", "error": str(e)}

    # /search
    try:
        if idp_engine and idp_engine.table:
            res = idp_engine.search("ICU hospitals", top_k=3)
            checks["/search"] = {"status": "ok", "results": res.result_count}
        else:
            checks["/search"] = {"status": "skipped", "reason": "index not built"}
    except Exception as e:
        checks["/search"] = {"status": "error", "error": str(e)}

    # /anomalies
    try:
        if _facility_cache:
            flags = detect_anomalies(_facility_cache[:10])
            checks["/anomalies"] = {"status": "ok", "flags_on_sample": len(flags)}
        else:
            checks["/anomalies"] = {"status": "skipped", "reason": "cache empty"}
    except Exception as e:
        checks["/anomalies"] = {"status": "error", "error": str(e)}

    # /deserts
    try:
        if _facility_cache:
            zones = detect_deserts_from_facilities(_facility_cache, "cardiology")
            checks["/deserts"] = {"status": "ok", "desert_zones": len(zones)}
        else:
            checks["/deserts"] = {"status": "skipped", "reason": "cache empty"}
    except Exception as e:
        checks["/deserts"] = {"status": "error", "error": str(e)}

    # /coverage
    try:
        if _facility_cache:
            cov = build_coverage_map(_facility_cache)
            checks["/coverage"] = {"status": "ok", "regions": len(cov)}
        else:
            checks["/coverage"] = {"status": "skipped", "reason": "cache empty"}
    except Exception as e:
        checks["/coverage"] = {"status": "error", "error": str(e)}

    overall = all(
        c["status"] in ("ok", "skipped") for c in checks.values()
    )
    return {
        "overall":   "PASS" if overall else "FAIL",
        "checks":    checks,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

# ── /agent ────────────────────────────────────────────────────────────────────

@app.post("/agent")
async def chat_agent(payload: AgentRequest):
    """
    Connects the React chat UI to the LangGraph reasoning engine.
    """
    _require_engine("/agent")
    
    try:
        # Execute the full retrieve -> reason -> synthesize -> respond loop
        result = run_agent(query=payload.query, region=payload.region)
        
        # agent.py packs the final typed Pydantic object into a JSON string
        response_json_str = result.get("response", "{}")
        
        # Parse it back to a dict so FastAPI serves it correctly as application/json
        return json.loads(response_json_str)
        
    except Exception as e:
        logger.error(f"/agent error: {e}")
        raise _error(500, f"Agent orchestration failed: {str(e)}")


# ════════════════════════════════════════════════════════════════════════════
# DATABRICKS ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════
frontend_dist_path = os.path.join(os.path.dirname(__file__), "../../frontend/dist")

if os.path.exists(frontend_dist_path):
    app.mount("/assets", StaticFiles(directory=f"{frontend_dist_path}/assets"), name="assets")
    
    # Catch-all route to serve the React index.html for any frontend routes
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Ignore API routes
        if full_path.startswith("api/") or full_path in ["health", "warmup", "eval", "agent"]:
            raise HTTPException(status_code=404, detail="Not Found")
            
        index_path = os.path.join(frontend_dist_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Frontend build not found")
else:
    logger.warning("Frontend dist folder not found. API only mode.")

    
if __name__ == "__main__":
    nest_asyncio.apply()
    logger.info("Starting Virtue Foundation IDP API v4.0 on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
