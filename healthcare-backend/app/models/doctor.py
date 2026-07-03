

"""
SQLAlchemy Doctor model.

A Doctor record extends a User (role=DOCTOR) with medical-profile fields.
"""
import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    doctor_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # One-to-one link back to the users table (the DOCTOR-role account).
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    specialization = Column(String(150), nullable=False, index=True)
    qualification = Column(String(255), nullable=False)
    experience = Column(Integer, nullable=False, default=0)  # years of experience

    # Structured working hours, e.g.:
    # {"days": ["MON", "TUE", "WED", "THU", "FRI"], "start_time": "09:00", "end_time": "17:00"}
    working_hours = Column(JSON, nullable=False)

    slot_duration = Column(Integer, nullable=False, default=30)  # minutes per appointment slot
    consultation_fee = Column(Numeric(10, 2), nullable=False, default=0)

    # True while the doctor is currently on leave / unavailable for booking.
    leave_status = Column(Boolean, nullable=False, default=False)

    user = relationship("User", backref="doctor_profile", uselist=False)

    def __repr__(self) -> str:
        return f"<Doctor id={self.doctor_id} specialization={self.specialization}>"
