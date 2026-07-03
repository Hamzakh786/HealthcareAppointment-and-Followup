"""
Pydantic schemas for the Patient module.
"""
import re
import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

PHONE_REGEX = re.compile(r"^\+?[0-9]{7,15}$")


class GenderEnum(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class BloodGroupEnum(str, Enum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"


# ---------------------------------------------------------------------------
# Base / shared
# ---------------------------------------------------------------------------
class PatientBase(BaseModel):
    age: int = Field(..., ge=0, le=120)
    gender: GenderEnum
    phone: str = Field(..., min_length=7, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    blood_group: Optional[BloodGroupEnum] = None
    medical_history: Optional[str] = Field(None, max_length=5000)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not PHONE_REGEX.match(v):
            raise ValueError(
                "Phone number must contain 7-15 digits, with an optional leading '+'."
            )
        return v


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
class PatientCreate(PatientBase):
    user_id: int  # must reference an existing user with role=PATIENT


# ---------------------------------------------------------------------------
# Update (partial)
# ---------------------------------------------------------------------------
class PatientUpdate(BaseModel):
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[GenderEnum] = None
    phone: Optional[str] = Field(None, min_length=7, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    blood_group: Optional[BloodGroupEnum] = None
    medical_history: Optional[str] = Field(None, max_length=5000)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not PHONE_REGEX.match(v):
            raise ValueError(
                "Phone number must contain 7-15 digits, with an optional leading '+'."
            )
        return v


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------
class PatientResponse(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    patient_id: uuid.UUID
    user_id: int


class PatientListResponse(BaseModel):
    total: int
    results: List[PatientResponse]
