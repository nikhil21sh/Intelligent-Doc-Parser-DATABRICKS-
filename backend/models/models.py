from pydantic import BaseModel, Field
from typing import List, Optional

class OrganizationBase(BaseModel):
    """Essential fields for any entity tracked in Ghana"""
    name: str = Field(..., description="Name of the entity")
    location: str = Field(..., description="Region or town")
    contact_info: Optional[str] = None

class FacilityFact(OrganizationBase):
    """Structured data for hospital/clinic extraction"""
    specialties: List[str] = Field(default_factory=list)
    procedure: List[str] = Field(default_factory=list, description="Extracted medical procedures")
    equipment: List[str] = Field(default_factory=list, description="Medical devices found")
    capability: List[str] = Field(default_factory=list, description="ICU, Trauma levels, etc.")
    num_doctors: Optional[int] = 0

class NGOFact(OrganizationBase):
    """Structured data for NGOs and mission groups"""
    focus_area: List[str] = Field(default_factory=list, description="e.g., Cardiology, Maternal Health")
    mission_duration: Optional[str] = None
    target_demographic: Optional[str] = None

class ExtractionResponse(BaseModel):
    data: FacilityFact # You can update this to Union[FacilityFact, NGOFact] later
    confidence_score: float
    metadata: dict