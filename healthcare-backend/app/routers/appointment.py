"""
Appointment routes.

Access rules:
  - Book             -> ADMIN, or the PATIENT booking for themselves
  - Get               -> ADMIN, the owning DOCTOR, or the owning PATIENT
  - List               -> ADMIN (any filter); DOCTOR/PATIENT auto-scoped to their own records
  - Cancel            -> ADMIN, the owning DOCTOR, or the owning PATIENT
  - Reschedule        -> ADMIN, the owning DOCTOR, or the owning PATIENT
  - Update status     -> ADMIN or the owning DOCTOR (clinical workflow)
  - Doctor availability -> any authenticated user
"""
import uuid
from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.appointment import Appointment, AppointmentStatus as ORMAppointmentStatus
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import RoleEnum, User
from app.schemas.appointment import (
    AppointmentCancel,
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentReschedule,
    AppointmentResponse,
    AppointmentStatus,
    AppointmentStatusUpdate,
    AvailableSlotsResponse,
)
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments", tags=["Appointments"])


# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------
def _doctor_owns(db: Session, current_user: User, doctor_id: uuid.UUID) -> bool:
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    return bool(doctor) and current_user.role == RoleEnum.DOCTOR and doctor.user_id == current_user.id


def _patient_owns(db: Session, current_user: User, patient_id: uuid.UUID) -> bool:
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    return bool(patient) and current_user.role == RoleEnum.PATIENT and patient.user_id == current_user.id


def _ensure_can_access(db: Session, current_user: User, appointment: Appointment) -> None:
    if current_user.role == RoleEnum.ADMIN:
        return
    if _doctor_owns(db, current_user, appointment.doctor_id):
        return
    if _patient_owns(db, current_user, appointment.patient_id):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to access this appointment.",
    )


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------
@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def book_appointment(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Book a new appointment. Patients may only book for themselves; Admins may book
    on behalf of any patient. Doctor availability and slot conflicts are validated
    inside a single database transaction to prevent double/simultaneous booking."""
    if current_user.role not in (RoleEnum.ADMIN, RoleEnum.PATIENT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or patients can book appointments.",
        )
    if current_user.role == RoleEnum.PATIENT and not _patient_owns(
        db, current_user, payload.patient_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients may only book appointments for themselves.",
        )
    return AppointmentService.book_appointment(db, payload)


# ---------------------------------------------------------------------------
# Doctor availability
# ---------------------------------------------------------------------------
@router.get("/availability/{doctor_id}", response_model=AvailableSlotsResponse)
def get_doctor_availability(
    doctor_id: uuid.UUID,
    target_date: date_type = Query(..., alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return this doctor's free appointment slots for a given date."""
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found.")
    slots = AppointmentService.get_available_slots(db, doctor_id, target_date)
    return AvailableSlotsResponse(
        doctor_id=doctor_id,
        date=target_date,
        slot_duration_minutes=doctor.slot_duration,
        available_slots=slots,
    )


# ---------------------------------------------------------------------------
# List (scoped by role)
# ---------------------------------------------------------------------------
@router.get("", response_model=AppointmentListResponse)
def list_appointments(
    doctor_id: Optional[uuid.UUID] = Query(None),
    patient_id: Optional[uuid.UUID] = Query(None),
    appointment_status: Optional[AppointmentStatus] = Query(None, alias="status"),
    from_date: Optional[date_type] = Query(None),
    to_date: Optional[date_type] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List appointments. Admins may filter freely; doctors and patients are
    automatically scoped to their own appointments regardless of the filters passed."""
    if current_user.role == RoleEnum.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        doctor_id = doctor.doctor_id if doctor else uuid.uuid4()  # no profile -> no results
    elif current_user.role == RoleEnum.PATIENT:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        patient_id = patient.patient_id if patient else uuid.uuid4()

    orm_status = ORMAppointmentStatus(appointment_status.value) if appointment_status else None

    results = AppointmentService.list_appointments(
        db, doctor_id, patient_id, orm_status, from_date, to_date, skip, limit
    )
    total = AppointmentService.count_appointments(
        db, doctor_id, patient_id, orm_status, from_date, to_date
    )
    return AppointmentListResponse(total=total, results=results)


# ---------------------------------------------------------------------------
# Get by id
# ---------------------------------------------------------------------------
@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = AppointmentService.get_appointment_by_id(db, appointment_id)
    _ensure_can_access(db, current_user, appointment)
    return appointment


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------
@router.patch("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = AppointmentService.get_appointment_by_id(db, appointment_id)
    _ensure_can_access(db, current_user, appointment)
    return AppointmentService.cancel_appointment(db, appointment_id)


# ---------------------------------------------------------------------------
# Reschedule
# ---------------------------------------------------------------------------
@router.patch("/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentReschedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = AppointmentService.get_appointment_by_id(db, appointment_id)
    _ensure_can_access(db, current_user, appointment)
    return AppointmentService.reschedule_appointment(db, appointment_id, payload)


# ---------------------------------------------------------------------------
# Status update (clinical workflow, e.g. CONFIRMED / COMPLETED / NO_SHOW)
# ---------------------------------------------------------------------------
@router.patch("/{appointment_id}/status", response_model=AppointmentResponse)
def update_appointment_status(
    appointment_id: uuid.UUID,
    payload: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = AppointmentService.get_appointment_by_id(db, appointment_id)
    if current_user.role == RoleEnum.ADMIN or _doctor_owns(
        db, current_user, appointment.doctor_id
    ):
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the treating doctor or an admin can update appointment status.",
        )
    new_status = ORMAppointmentStatus(payload.status.value)
    return AppointmentService.update_status(
        db, appointment_id, new_status, payload.ai_summary
    )
