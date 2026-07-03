"""
Appointment business logic: CRUD operations, availability checks, and scheduling.
"""
import uuid
from datetime import date as date_type
from datetime import datetime, time as time_type
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.appointment import AppointmentCreate, AppointmentReschedule


class AppointmentService:
    """Service for managing appointments."""

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------
    @staticmethod
    def get_appointment_by_id(db: Session, appointment_id: uuid.UUID) -> Appointment:
        """Fetch an appointment by ID, or raise 404."""
        appointment = db.query(Appointment).filter(
            Appointment.appointment_id == appointment_id
        ).first()
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found.",
            )
        return appointment

    # ------------------------------------------------------------------
    # Create / Book
    # ------------------------------------------------------------------
    @staticmethod
    def book_appointment(db: Session, payload: AppointmentCreate) -> Appointment:
        """
        Book a new appointment.
        
        Validates:
          - Doctor exists and is not on leave
          - Patient exists
          - Doctor is available at the requested time
          - No slot conflict (enforced by unique index at DB level)
        
        Uses SELECT ... FOR UPDATE on the doctor row to serialize concurrent
        bookings for the same doctor.
        """
        # Fetch doctor with lock to prevent concurrent double-booking
        doctor = db.query(Doctor).filter(
            Doctor.doctor_id == payload.doctor_id
        ).with_for_update().first()

        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found.",
            )

        if doctor.leave_status:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Doctor is currently on leave.",
            )

        # Validate patient exists
        patient = db.query(Patient).filter(
            Patient.patient_id == payload.patient_id
        ).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found.",
            )

        # Check if the time slot is available (within working hours)
        if not AppointmentService._is_within_working_hours(doctor, payload.date, payload.time):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Requested time is outside doctor's working hours.",
            )

        # Check for existing active appointments at this slot
        existing = db.query(Appointment).filter(
            and_(
                Appointment.doctor_id == payload.doctor_id,
                Appointment.date == payload.date,
                Appointment.time == payload.time,
                Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Requested time slot is already booked.",
            )

        # Create and save
        appointment = Appointment(
            doctor_id=payload.doctor_id,
            patient_id=payload.patient_id,
            date=payload.date,
            time=payload.time,
            symptoms=payload.symptoms,
            urgency=payload.urgency,
            status=AppointmentStatus.PENDING,
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        return appointment

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------
    @staticmethod
    def get_available_slots(
        db: Session,
        doctor_id: uuid.UUID,
        target_date: date_type,
    ) -> List[str]:
        """
        Return available appointment slots (HH:MM format) for a doctor on a given date.
        """
        doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
        if not doctor:
            return []

        if doctor.leave_status:
            return []

        # Get working hours
        working_hours = doctor.working_hours  # e.g. {"start_time": "09:00", "end_time": "17:00", ...}
        if not working_hours or "start_time" not in working_hours or "end_time" not in working_hours:
            return []

        try:
            start_str = working_hours["start_time"]
            end_str = working_hours["end_time"]
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()
        except (ValueError, KeyError, TypeError):
            return []

        slot_duration = doctor.slot_duration  # minutes

        # Get all active appointments for this doctor on this date
        booked = db.query(Appointment.time).filter(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.date == target_date,
                Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
            )
        ).all()
        booked_times = {t[0] for t in booked}

        # Generate available slots
        slots = []
        current = datetime.combine(target_date, start_time)
        end = datetime.combine(target_date, end_time)

        while current < end:
            slot_time = current.time()
            if slot_time not in booked_times:
                slots.append(slot_time.strftime("%H:%M"))
            current = datetime.fromtimestamp(
                current.timestamp() + slot_duration * 60
            )

        return slots

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------
    @staticmethod
    def list_appointments(
        db: Session,
        doctor_id: Optional[uuid.UUID] = None,
        patient_id: Optional[uuid.UUID] = None,
        status: Optional[AppointmentStatus] = None,
        from_date: Optional[date_type] = None,
        to_date: Optional[date_type] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Appointment]:
        """List appointments with optional filters."""
        query = db.query(Appointment)

        if doctor_id:
            query = query.filter(Appointment.doctor_id == doctor_id)
        if patient_id:
            query = query.filter(Appointment.patient_id == patient_id)
        if status:
            query = query.filter(Appointment.status == status)
        if from_date:
            query = query.filter(Appointment.date >= from_date)
        if to_date:
            query = query.filter(Appointment.date <= to_date)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def count_appointments(
        db: Session,
        doctor_id: Optional[uuid.UUID] = None,
        patient_id: Optional[uuid.UUID] = None,
        status: Optional[AppointmentStatus] = None,
        from_date: Optional[date_type] = None,
        to_date: Optional[date_type] = None,
    ) -> int:
        """Count appointments matching filters."""
        query = db.query(func.count(Appointment.appointment_id))

        if doctor_id:
            query = query.filter(Appointment.doctor_id == doctor_id)
        if patient_id:
            query = query.filter(Appointment.patient_id == patient_id)
        if status:
            query = query.filter(Appointment.status == status)
        if from_date:
            query = query.filter(Appointment.date >= from_date)
        if to_date:
            query = query.filter(Appointment.date <= to_date)

        return query.scalar() or 0

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    @staticmethod
    def cancel_appointment(db: Session, appointment_id: uuid.UUID) -> Appointment:
        """Cancel an appointment (set status to CANCELLED)."""
        appointment = AppointmentService.get_appointment_by_id(db, appointment_id)

        if appointment.status == AppointmentStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Appointment is already cancelled.",
            )

        appointment.status = AppointmentStatus.CANCELLED
        appointment.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(appointment)
        return appointment

    @staticmethod
    def reschedule_appointment(
        db: Session,
        appointment_id: uuid.UUID,
        payload: AppointmentReschedule,
    ) -> Appointment:
        """Reschedule an appointment to a new date/time."""
        appointment = AppointmentService.get_appointment_by_id(db, appointment_id)

        if appointment.status == AppointmentStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot reschedule a cancelled appointment.",
            )

        if appointment.status == AppointmentStatus.RESCHEDULED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Appointment has already been rescheduled.",
            )

        # Fetch doctor
        doctor = db.query(Doctor).filter(
            Doctor.doctor_id == appointment.doctor_id
        ).with_for_update().first()

        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found.",
            )

        if doctor.leave_status:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Doctor is on leave; cannot reschedule.",
            )

        # Check if new time is within working hours
        if not AppointmentService._is_within_working_hours(doctor, payload.date, payload.time):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="New time is outside doctor's working hours.",
            )

        # Check for conflicts at new slot
        conflict = db.query(Appointment).filter(
            and_(
                Appointment.doctor_id == appointment.doctor_id,
                Appointment.date == payload.date,
                Appointment.time == payload.time,
                Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
                Appointment.appointment_id != appointment_id,  # exclude self
            )
        ).first()

        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="New time slot is already booked.",
            )

        # Mark original as RESCHEDULED and create new appointment
        appointment.status = AppointmentStatus.RESCHEDULED
        appointment.updated_at = datetime.utcnow()

        new_appointment = Appointment(
            doctor_id=appointment.doctor_id,
            patient_id=appointment.patient_id,
            date=payload.date,
            time=payload.time,
            symptoms=appointment.symptoms,
            urgency=appointment.urgency,
            status=AppointmentStatus.PENDING,
        )
        db.add(new_appointment)
        db.commit()
        db.refresh(new_appointment)
        return new_appointment

    @staticmethod
    def update_status(
        db: Session,
        appointment_id: uuid.UUID,
        new_status: AppointmentStatus,
        ai_summary: Optional[str] = None,
    ) -> Appointment:
        """Update appointment status and optional AI summary."""
        appointment = AppointmentService.get_appointment_by_id(db, appointment_id)

        # Validate state transitions
        if appointment.status == AppointmentStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot update a cancelled appointment.",
            )

        appointment.status = new_status
        if ai_summary is not None:
            appointment.ai_summary = ai_summary
        appointment.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(appointment)
        return appointment

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _is_within_working_hours(
        doctor: Doctor,
        target_date: date_type,
        target_time: time_type,
    ) -> bool:
        """Check if target_time falls within doctor's working hours for target_date."""
        working_hours = doctor.working_hours
        if not working_hours:
            return False

        try:
            # Check if target_date is a working day
            days = working_hours.get("days", [])
            day_name = target_date.strftime("%a").upper()  # MON, TUE, etc.
            if days and day_name not in days:
                return False

            start_str = working_hours.get("start_time", "09:00")
            end_str = working_hours.get("end_time", "17:00")
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()

            return start_time <= target_time < end_time
        except (ValueError, KeyError, TypeError, AttributeError):
            return False