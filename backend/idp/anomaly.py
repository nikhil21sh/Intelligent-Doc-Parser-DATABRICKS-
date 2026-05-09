"""
backend/idp/anomaly.py
======================
Day 3 new file — anomaly detection rule engine.

Implements 3 rule types with confidence scores:
  Rule 1 — ICU claim without documented backup power
  Rule 2 — >3 specialties without matching imaging equipment
  Rule 3 — High capacity (>200 beds) with very few doctors (<2)

Each rule returns an AnomalyFlag with a confidence score (0–1).
Results stored in the flagged_facilities Delta table (see notebooks/).
Exposed via GET /anomalies in main.py.
"""

from typing import List, Dict, Any
from backend.models.models import AnomalyFlag, FacilityFact


# ── Keyword lists for rule matching ──────────────────────────────────────────

ICU_KEYWORDS     = ["icu", "intensive care unit", "intensive care", "critical care"]
BACKUP_KEYWORDS  = ["backup generator", "generator", "backup power", "ups", "inverter",
                    "diesel generator", "standby power"]
IMAGING_KEYWORDS = ["mri", "ct scanner", "ct scan", "x-ray", "xray", "ultrasound",
                    "mammogram", "fluoroscopy", "pet scan"]


def _text_contains_any(text: str, keywords: List[str]) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


# ── Individual rule functions ─────────────────────────────────────────────────

def rule_icu_without_backup_power(facility: FacilityFact) -> List[AnomalyFlag]:
    """
    Rule 1: Facility claims ICU but no backup power is documented in equipment.
    Rationale: Power outages in Northern/Upper regions are frequent.
               An ICU without backup power is a critical patient safety risk.
    Confidence: 0.90 if ICU mentioned in capability only,
                0.75 if ICU in description only (less reliable source).
    """
    flags = []

    cap_text   = " ".join(facility.capability or [])
    equip_text = " ".join(facility.equipment  or [])
    desc_text  = facility.description or ""

    has_icu_capability   = _text_contains_any(cap_text,  ICU_KEYWORDS)
    has_icu_description  = _text_contains_any(desc_text, ICU_KEYWORDS)
    has_backup_power     = _text_contains_any(equip_text, BACKUP_KEYWORDS)

    if has_backup_power:
        return []   # no flag — backup power documented

    if has_icu_capability:
        flags.append(AnomalyFlag(
            facility_id   = facility.row_id or facility.name,
            facility_name = facility.name,
            flag_type     = "ICU_WITHOUT_BACKUP_POWER",
            confidence    = 0.90,
            reason        = (
                f"{facility.name} claims ICU capability but no backup generator, UPS, "
                f"or standby power source is listed in the equipment field. "
                f"Power failures will disable ICU equipment and endanger patients."
            ),
            severity      = "high"
        ))
    elif has_icu_description:
        flags.append(AnomalyFlag(
            facility_id   = facility.row_id or facility.name,
            facility_name = facility.name,
            flag_type     = "ICU_WITHOUT_BACKUP_POWER",
            confidence    = 0.75,
            reason        = (
                f"{facility.name} mentions ICU in description but no backup power is documented. "
                f"Confidence reduced as source is description rather than structured capability field."
            ),
            severity      = "high"
        ))

    return flags


def rule_specialty_without_imaging(facility: FacilityFact) -> List[AnomalyFlag]:
    """
    Rule 2: Facility claims >3 specialties but no imaging equipment is documented.
    Rationale: A facility with 4+ specialties (cardiology, surgery, etc.)
               operating without any imaging (X-ray, ultrasound at minimum)
               is either under-reporting equipment or making suspicious claims.
    Confidence: 0.80 (strong signal — imaging is a near-universal requirement).
    """
    flags = []

    equip_text     = " ".join(facility.equipment or [])
    has_imaging    = _text_contains_any(equip_text, IMAGING_KEYWORDS)
    specialty_count= len(facility.specialties or [])

    if specialty_count > 3 and not has_imaging:
        flags.append(AnomalyFlag(
            facility_id   = facility.row_id or facility.name,
            facility_name = facility.name,
            flag_type     = "MULTIPLE_SPECIALTIES_WITHOUT_IMAGING",
            confidence    = 0.80,
            reason        = (
                f"{facility.name} claims {specialty_count} specialties "
                f"({', '.join(facility.specialties[:4])}) but no imaging equipment "
                f"(MRI, CT, X-ray, or ultrasound) is documented. "
                f"Verify equipment completeness before routing patients."
            ),
            severity      = "medium"
        ))

    return flags


def rule_high_capacity_low_doctors(facility: FacilityFact) -> List[AnomalyFlag]:
    """
    Rule 3: Facility claims >200 bed capacity with fewer than 2 doctors.
    Rationale: A 200+ bed hospital run by 0–1 doctors is almost certainly
               an under-reporting error or a suspicious claim.
               WHO recommends ~1 doctor per 43 inpatients as a minimum.
    Confidence: 0.85 if capacity >200 and doctors <2,
                0.70 if capacity >500 and doctors <5 (less obvious threshold).
    """
    flags = []

    capacity    = facility.capacity    or 0
    num_doctors = facility.num_doctors or 0

    if capacity > 200 and num_doctors < 2:
        flags.append(AnomalyFlag(
            facility_id   = facility.row_id or facility.name,
            facility_name = facility.name,
            flag_type     = "HIGH_CAPACITY_LOW_DOCTORS",
            confidence    = 0.85,
            reason        = (
                f"{facility.name} reports {capacity} bed capacity but only "
                f"{num_doctors} doctor(s). "
                f"WHO minimum is ~1 doctor per 43 inpatients. "
                f"Verify staffing data before routing patients."
            ),
            severity      = "high"
        ))
    elif capacity > 500 and num_doctors < 5:
        flags.append(AnomalyFlag(
            facility_id   = facility.row_id or facility.name,
            facility_name = facility.name,
            flag_type     = "HIGH_CAPACITY_LOW_DOCTORS",
            confidence    = 0.70,
            reason        = (
                f"{facility.name} reports {capacity} bed capacity with only "
                f"{num_doctors} doctors. Staffing appears insufficient for reported capacity."
            ),
            severity      = "medium"
        ))

    return flags


# ── Main public function ──────────────────────────────────────────────────────

def detect_anomalies(facilities: List[FacilityFact]) -> List[AnomalyFlag]:
    """
    Runs all 3 anomaly rules over a list of facilities.
    Returns a flat list of all AnomalyFlag objects found.
    Called by: GET /anomalies endpoint in main.py.

    To run over the entire Delta Lake table (from a Databricks notebook):
        from backend.idp.anomaly import detect_anomalies
        from backend.models.models import FacilityFact

        df      = spark.sql("SELECT * FROM main.hackathon.facilities")
        records = [FacilityFact(**row.asDict()) for row in df.collect()]
        flags   = detect_anomalies(records)
        # Then write flags back to a flagged_facilities Delta table
    """
    all_flags = []

    rules = [
        rule_icu_without_backup_power,
        rule_specialty_without_imaging,
        rule_high_capacity_low_doctors,
    ]

    for facility in facilities:
        for rule_fn in rules:
            try:
                flags = rule_fn(facility)
                all_flags.extend(flags)
            except Exception as e:
                # A rule failure must never crash the entire endpoint
                print(f"  [anomaly] rule {rule_fn.__name__} failed on "
                      f"'{facility.name}': {e}")

    return all_flags


def detect_anomalies_from_dicts(
    facility_dicts: List[Dict[str, Any]]
) -> List[AnomalyFlag]:
    """
    Convenience wrapper — accepts raw dicts from Delta Lake rows
    instead of FacilityFact objects. Handles partial/missing fields gracefully.
    Called by: GET /anomalies when facility_ids param is provided.
    """
    facilities = []
    for d in facility_dicts:
        try:
            # Fill required fields with defaults if missing
            d.setdefault("name",     d.get("name", "Unknown"))
            d.setdefault("location", d.get("address_state_or_region", "Unknown"))
            facilities.append(FacilityFact(**d))
        except Exception as e:
            print(f"  [anomaly] could not parse facility dict: {e}")
            continue

    return detect_anomalies(facilities)