"""
Pydantic schemas for the Appointment module.
"""
import uuid
from datetime import date as date_type
from datetime import time as time_type
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AppointmentStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"


class UrgencyEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"


# ---------------------------------------------------------------------------
# Create / Book
# ---------------------------------------------------------------------------
class AppointmentCreate(BaseModel):
    doctor_id: uuid.UUID
    patient_id: uuid.UUID
    date: date_type
    time: time_type
    symptoms: Optional[str] = Field(None, max_length=2000)
    urgency: UrgencyEnum = UrgencyEnum.LOW

    @field_validator("date")
    @classmethod
    def date_not_in_past(cls, v: date_type) -> date_type:
        if v < date_type.today():
            raise ValueError("Appointment date cannot be in the past.")
        return v


# ---------------------------------------------------------------------------
# Reschedule
# ---------------------------------------------------------------------------
class AppointmentReschedule(BaseModel):
    date: date_type
    time: time_type

    @field_validator("date")
    @classmethod
    def date_not_in_past(cls, v: date_type) -> date_type:
        if v < date_type.today():
            raise ValueError("Appointment date cannot be in the past.")
        return v


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------
class AppointmentCancel(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


# ---------------------------------------------------------------------------
# Status update (doctor/admin workflow: PENDING -> CONFIRMED -> COMPLETED, etc.)
# ---------------------------------------------------------------------------
class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus
    ai_summary: Optional[str] = Field(None, max_length=4000)


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------
class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    appointment_id: uuid.UUID
    doctor_id: uuid.UUID
    patient_id: uuid.UUID
    date: date_type
    time: time_type
    status: AppointmentStatus
    symptoms: Optional[str] = None
    ai_summary: Optional[str] = None
    urgency: UrgencyEnum


class AppointmentListResponse(BaseModel):
    total: int
    results: List[AppointmentResponse]


class AvailableSlotsResponse(BaseModel):
    doctor_id: uuid.UUID
    date: date_type
    slot_duration_minutes: int
    available_slots: List[time_type]
