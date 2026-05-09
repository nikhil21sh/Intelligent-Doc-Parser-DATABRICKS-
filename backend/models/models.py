from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# ── Base ─────────────────────────────────────────────────────────────────────

class OrganizationBase(BaseModel):
    """Essential fields for any entity tracked in Ghana."""
    name:         str           = Field(...,  description="Official name of the entity")
    location:     str           = Field(...,  description="Region or town — maps to address_stateOrRegion")
    contact_info: Optional[str] = Field(None, description="Primary phone or email")


# ── Core facility model ───────────────────────────────────────────────────────

class FacilityFact(OrganizationBase):
    """
    Structured data for hospital/clinic extraction.
    Extended Day 2: added all schema fields the agent and map UI need.
    row_id is the Delta Lake primary key — used for step-level citations.
    """
    # Identity
    row_id:               Optional[str]   = Field(None, description="Delta Lake primary key — required for citations")

    # Classification
    facility_type_id:     Optional[str]   = Field(None, description="hospital|pharmacy|doctor|clinic|dentist")
    operator_type_id:     Optional[str]   = Field(None, description="public|private")
    affiliation_type_ids: List[str]       = Field(default_factory=list)

    # IDP free-form fields (extracted by MedicalIDP)
    specialties:          List[str]       = Field(default_factory=list)
    procedure:            List[str]       = Field(default_factory=list)
    equipment:            List[str]       = Field(default_factory=list)
    capability:           List[str]       = Field(default_factory=list)

    # Structured numeric fields
    num_doctors:          Optional[int]   = Field(0)
    capacity:             Optional[int]   = Field(None)
    area:                 Optional[int]   = Field(None)
    year_established:     Optional[int]   = Field(None)
    accepts_volunteers:   Optional[bool]  = Field(None)

    # Address
    address_city:             Optional[str] = Field(None)
    address_state_or_region:  Optional[str] = Field(None)
    address_country:          Optional[str] = Field( default="Ghana")
    address_country_code:     Optional[str] = Field( default="GH")

    # Geolocation — required by Intern 3 map
    latitude:             Optional[float] = Field(None)
    longitude:            Optional[float] = Field(None)

    # Contact
    phone_numbers:        List[str]       = Field(default_factory=list)
    official_phone:       Optional[str]   = Field(None)
    email:                Optional[str]   = Field(None)
    official_website:     Optional[str]   = Field(None)
    description:          Optional[str]   = Field(None)


# ── NGO model ─────────────────────────────────────────────────────────────────

class NGOFact(OrganizationBase):
    """Structured data for NGOs and mission groups."""
    focus_area:         List[str]      = Field(default_factory=list)
    mission_duration:   Optional[str]  = Field(None)
    target_demographic: Optional[str]  = Field(None)
    countries:          List[str]      = Field(default_factory=list)
    mission_statement:  Optional[str]  = Field(None)
    accepts_volunteers: Optional[bool] = Field(None)


# ── Anomaly detection models ──────────────────────────────────────────────────

class AnomalyFlag(BaseModel):
    """
    One rule violation on one facility.
    Consumed by: agent reason_node, frontend AnomalyBadge component.
    """
    facility_id:   str   = Field(..., description="row_id of the flagged facility")
    facility_name: str   = Field(..., description="Human-readable name for UI display")
    flag_type:     str   = Field(..., description="e.g. ICU_WITHOUT_BACKUP_POWER")
    confidence:    float = Field(..., ge=0.0, le=1.0)
    reason:        str   = Field(..., description="Plain-English explanation")
    severity:      str   = Field("medium", description="low|medium|high")


# ── Medical desert model ──────────────────────────────────────────────────────

class DesertZone(BaseModel):
    """
    A region with zero/critically low coverage for a specialty.
    Consumed by: agent reason_node, frontend heatmap overlay.
    """
    region:               str            = Field(...)
    specialty:            str            = Field(...)
    facility_count:       int            = Field(...)
    nearest_facility:     Optional[str]  = Field(None)
    nearest_distance_km:  Optional[float]= Field(None)
    severity:             str            = Field("critical", description="critical|high|medium")


# ── Search result model ───────────────────────────────────────────────────────

class SearchResult(BaseModel):
    """Output of /search — consumed by agent retrieve_node."""
    facilities:   List[FacilityFact] = Field(default_factory=list)
    confidence:   float              = Field(..., ge=0.0, le=1.0)
    query:        str                = Field(...)
    result_count: int                = Field(...)


# ── API request/response wrappers ─────────────────────────────────────────────

class DocumentRequest(BaseModel):
    """POST /extract request body."""
    text: str = Field(..., min_length=20)


class SearchRequest(BaseModel):
    """POST /search request body."""
    q:         str           = Field(...)
    region:    Optional[str] = Field(None)
    specialty: Optional[str] = Field(None)
    top_k:     int           = Field(5, ge=1, le=20)


class ExtractionResponse(BaseModel):
    """POST /extract response envelope."""
    status:           str              = Field("success")
    data:             FacilityFact
    confidence_score: float            = Field(..., ge=0.0, le=1.0)
    metadata:         Dict[str, Any]   = Field(default_factory=dict)


class AnomalyResponse(BaseModel):
    """GET /anomalies response envelope."""
    flags:       List[AnomalyFlag] = Field(default_factory=list)
    total_flags: int               = Field(0)
    region:      Optional[str]     = Field(None)


class DesertResponse(BaseModel):
    """GET /deserts response envelope."""
    zones:       List[DesertZone] = Field(default_factory=list)
    specialty:   str
    region:      Optional[str]   = Field(None)
    total_zones: int             = Field(0)