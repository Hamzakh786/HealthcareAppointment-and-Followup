
"""
SQLAlchemy Appointment model.

Double-booking protection is enforced at two levels:
  1. Application level - the booking transaction takes a row lock on the
     Doctor record (SELECT ... FOR UPDATE) before checking for conflicts,
     which serializes concurrent booking attempts for the same doctor.
  2. Database level - a partial unique index on (doctor_id, date, time)
     for "active" statuses guarantees no two active appointments can ever
     occupy the same doctor slot, even under concurrent transactions that
     bypass the application lock.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Text,
    Time,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base



class AppointmentStatus(str, enum.Enum):
    PENDING = "PENDING"  # booked, awaiting doctor confirmation
    CONFIRMED = "CONFIRMED"  # confirmed by doctor/system
    CANCELLED = "CANCELLED"  # cancelled by patient/doctor/admin
    RESCHEDULED = "RESCHEDULED"  # superseded by a new date/time (terminal, kept for history)
    COMPLETED = "COMPLETED"  # visit took place
    NO_SHOW = "NO_SHOW"  # patient did not show up

    @classmethod
    def active_statuses(cls) -> list:
        """Statuses that occupy a doctor's calendar slot."""
        return [cls.PENDING, cls.CONFIRMED]


class UrgencyEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        # Partial unique index: only PENDING/CONFIRMED rows count as
        # occupying the slot, so cancelled/rescheduled history doesn't
        # block rebooking the same slot.
        Index(
            "uq_doctor_active_slot",
            "doctor_id",
            "date",
            "time",
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'CONFIRMED')"),
        ),
        Index("ix_appointments_doctor_date", "doctor_id", "date"),
        Index("ix_appointments_patient_date", "patient_id", "date"),
    )

    appointment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    doctor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("doctors.doctor_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)

    status = Column(
        SqlEnum(AppointmentStatus), nullable=False, default=AppointmentStatus.PENDING
    )
    symptoms = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)  # populated by an AI triage/summary service
    urgency = Column(SqlEnum(UrgencyEnum), nullable=False, default=UrgencyEnum.LOW)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    doctor = relationship("Doctor", backref="appointments")
    patient = relationship("Patient", backref="appointments")

    def __repr__(self) -> str:
        return (
            f"<Appointment id={self.appointment_id} doctor={self.doctor_id} "
            f"patient={self.patient_id} {self.date} {self.time} status={self.status}>"
        )
