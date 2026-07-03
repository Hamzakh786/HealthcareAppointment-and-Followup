"""
SQLAlchemy Patient model.

A Patient record extends a User (role=PATIENT) with medical-profile fields.
"""

import enum
import uuid

from sqlalchemy import Column, Enum as SqlEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class GenderEnum(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class BloodGroupEnum(str, enum.Enum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"


class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    age = Column(Integer, nullable=False)
    gender = Column(SqlEnum(GenderEnum), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    address = Column(String(500), nullable=True)
    blood_group = Column(SqlEnum(BloodGroupEnum), nullable=True)
    medical_history = Column(Text, nullable=True)

    user = relationship("User", backref="patient_profile", uselist=False)

    def __repr__(self):
        return f"<Patient id={self.patient_id}>"