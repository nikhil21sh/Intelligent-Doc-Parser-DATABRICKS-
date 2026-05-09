"""
backend/idp/desert.py
=====================
Day 3 new file — medical desert detection.

A medical desert = a Ghana region with zero facilities offering a given specialty.

Two detection modes:
  detect_deserts_from_facilities() — works on an in-memory list of FacilityFact
  detect_deserts_from_delta()      — runs SQL directly on the Delta Lake table
                                     (use this from Databricks notebooks)

Exposed via GET /deserts?specialty=&region= in main.py.
"""

from typing import List, Optional, Dict, Any
from backend.models.models import FacilityFact, DesertZone

# All Ghana regions — used to identify which regions have zero facilities
GHANA_REGIONS = [
    "Greater Accra", "Ashanti", "Northern", "Upper East", "Upper West",
    "Western", "Central", "Eastern", "Volta", "Bono", "Savannah",
    "North East", "Oti", "Bono East", "Ahafo", "Western North"
]


def detect_deserts_from_facilities(
    facilities: List[FacilityFact],
    specialty:  str,
    region:     Optional[str] = None
) -> List[DesertZone]:
    """
    Identifies regions with zero facilities offering the given specialty.
    Works on an in-memory list — used when Delta Lake is not reachable.

    Args:
        facilities: full list of FacilityFact objects
        specialty:  specialty string to check (e.g. "cardiology")
        region:     if provided, only check this region; else check all Ghana regions

    Returns: list of DesertZone objects for regions with zero coverage
    """
    regions_to_check = [region] if region else GHANA_REGIONS

    # Build a map: region → count of facilities with this specialty
    coverage: Dict[str, int] = {r: 0 for r in regions_to_check}

    for facility in facilities:
        fac_region = (
            facility.address_state_or_region or
            facility.location or
            ""
        ).strip()

        # Match region case-insensitively
        matched_region = next(
            (r for r in regions_to_check if r.lower() == fac_region.lower()),
            None
        )
        if matched_region is None:
            continue

        facility_specialties = [s.lower() for s in (facility.specialties or [])]
        if specialty.lower() in facility_specialties:
            coverage[matched_region] += 1

    # Build DesertZone for any region with zero (or very low) coverage
    desert_zones = []
    for region_name, count in coverage.items():
        if count == 0:
            desert_zones.append(DesertZone(
                region         = region_name,
                specialty      = specialty,
                facility_count = 0,
                severity       = "critical"
            ))
        elif count == 1:
            # Single-facility coverage = high risk (any closure = desert)
            desert_zones.append(DesertZone(
                region         = region_name,
                specialty      = specialty,
                facility_count = 1,
                severity       = "high"
            ))

    return desert_zones


def build_coverage_map(
    facilities: List[FacilityFact]
) -> Dict[str, Dict[str, int]]:
    """
    Builds a full coverage map: {region: {specialty: count}}.
    Used by the frontend heatmap to color all districts in one call.
    Exposed via GET /coverage in main.py.
    """
    coverage: Dict[str, Dict[str, int]] = {r: {} for r in GHANA_REGIONS}

    for facility in facilities:
        fac_region = (
            facility.address_state_or_region or
            facility.location or ""
        ).strip()

        matched_region = next(
            (r for r in GHANA_REGIONS if r.lower() == fac_region.lower()),
            None
        )
        if matched_region is None:
            continue

        for specialty in (facility.specialties or []):
            spec = specialty.strip()
            coverage[matched_region][spec] = (
                coverage[matched_region].get(spec, 0) + 1
            )

    return coverage


def detect_deserts_from_delta(spark, specialty: str, region: Optional[str] = None):
    """
    Runs desert detection directly on the Delta Lake table using Spark SQL.
    More efficient than loading all records into memory for large datasets.
    Call this from a Databricks notebook.

    Example:
        from backend.idp.desert import detect_deserts_from_delta
        zones = detect_deserts_from_delta(spark, specialty="cardiology")

    Returns: list of DesertZone objects
    """
    region_filter = f"AND address_state_or_region = '{region}'" if region else ""

    # Count facilities per region that mention the specialty
    # Note: specialties is stored as a JSON string in Delta Lake
    df = spark.sql(f"""
        SELECT
            address_state_or_region AS region,
            COUNT(*) AS facility_count
        FROM main.hackathon.facilities
        WHERE array_contains(
            from_json(specialties, 'ARRAY<STRING>'),
            '{specialty}'
        )
        {region_filter}
        GROUP BY address_state_or_region
    """)

    covered_regions = {row["region"]: row["facility_count"] for row in df.collect()}

    regions_to_check = [region] if region else GHANA_REGIONS
    desert_zones = []

    for region_name in regions_to_check:
        count = covered_regions.get(region_name, 0)
        if count == 0:
            desert_zones.append(DesertZone(
                region         = region_name,
                specialty      = specialty,
                facility_count = 0,
                severity       = "critical"
            ))
        elif count == 1:
            desert_zones.append(DesertZone(
                region         = region_name,
                specialty      = specialty,
                facility_count = 1,
                severity       = "high"
            ))

    return desert_zones