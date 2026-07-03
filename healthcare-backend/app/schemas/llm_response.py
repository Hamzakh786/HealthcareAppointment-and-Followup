from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.llm_response import LLMResponseType, LLMResponseStatus


# ---------------------------------------------------------------------------
# Request payloads
# ---------------------------------------------------------------------------

class PreVisitSummaryRequest(BaseModel):
    appointment_id: Optional[int] = None
    patient_name: str
    age: Optional[int] = None
    symptoms: str = Field(..., description="Patient-reported symptoms / chief complaint")
    medical_history: Optional[str] = Field(None, description="Relevant past medical history")
    current_medications: Optional[str] = Field(None, description="Medications the patient is currently on")


class PostVisitSummaryRequest(BaseModel):
    appointment_id: Optional[int] = None
    patient_name: str
    doctor_notes: str = Field(..., description="Raw doctor notes taken during the visit")
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None


class PrescriptionExplanationRequest(BaseModel):
    prescription_id: Optional[int] = None
    medicines: str = Field(..., description="Prescribed medicines, dosage and frequency")
    doctor_notes: Optional[str] = None
    patient_language_level: Optional[str] = Field(
        "simple", description="'simple' or 'detailed' — controls explanation complexity"
    )


# ---------------------------------------------------------------------------
# Response payload
# ---------------------------------------------------------------------------

class LLMResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    response_type: LLMResponseType
    status: LLMResponseStatus
    appointment_id: Optional[int] = None
    prescription_id: Optional[int] = None
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    model_name: str
    created_at: datetime
