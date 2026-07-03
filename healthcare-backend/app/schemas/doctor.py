"""
Pydantic schemas for the Doctor module.
"""
import uuid
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DayEnum(str, Enum):
    MON = "MON"
    TUE = "TUE"
    WED = "WED"
    THU = "THU"
    FRI = "FRI"
    SAT = "SAT"
    SUN = "SUN"


class WorkingHours(BaseModel):
    """Structured representation stored in Doctor.working_hours (JSON column)."""

    days: List[DayEnum] = Field(..., min_length=1)
    start_time: str = Field(..., description="24-hour HH:MM, e.g. '09:00'")
    end_time: str = Field(..., description="24-hour HH:MM, e.g. '17:00'")

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        import re

        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", v):
            raise ValueError("Time must be in 24-hour HH:MM format, e.g. '09:00'.")
        return v

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, v: str, info):
        start = info.data.get("start_time")
        if start and v <= start:
            raise ValueError("end_time must be later than start_time.")
        return v


# ---------------------------------------------------------------------------
# Base / shared
# ---------------------------------------------------------------------------
class DoctorBase(BaseModel):
    specialization: str = Field(..., min_length=2, max_length=150)
    qualification: str = Field(..., min_length=2, max_length=255)
    experience: int = Field(..., ge=0, le=70, description="Years of experience")
    working_hours: WorkingHours
    slot_duration: int = Field(..., gt=0, le=240, description="Minutes per slot")
    consultation_fee: Decimal = Field(..., ge=0)
    leave_status: bool = False


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
class DoctorCreate(DoctorBase):
    user_id: int  # must reference an existing user with role=DOCTOR


# ---------------------------------------------------------------------------
# Update (all fields optional / partial update)
# ---------------------------------------------------------------------------
class DoctorUpdate(BaseModel):
    specialization: Optional[str] = Field(None, min_length=2, max_length=150)
    qualification: Optional[str] = Field(None, min_length=2, max_length=255)
    experience: Optional[int] = Field(None, ge=0, le=70)
    working_hours: Optional[WorkingHours] = None
    slot_duration: Optional[int] = Field(None, gt=0, le=240)
    consultation_fee: Optional[Decimal] = Field(None, ge=0)
    leave_status: Optional[bool] = None


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------
class DoctorResponse(DoctorBase):
    model_config = ConfigDict(from_attributes=True)

    doctor_id: uuid.UUID
    user_id: int


class DoctorListResponse(BaseModel):
    total: int
    results: List[DoctorResponse]
