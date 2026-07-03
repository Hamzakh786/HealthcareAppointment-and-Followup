"""
router.py

Exposes each notification as its own endpoint, each queuing the send via
FastAPI's BackgroundTasks so the HTTP response returns immediately and the
SMTP call happens after the response is sent.

In practice you'll likely call `background_tasks.add_task(email_service.send_*, ...)`
directly from your existing appointment/prescription/reminder endpoints
rather than hitting these as standalone endpoints — they're included here
so the service is independently testable and usable from Postman/curl too.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, status
from pydantic import BaseModel, EmailStr

from app.services import email_service

router = APIRouter(prefix="/notifications/email", tags=["Email Notifications"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class AppointmentConfirmationRequest(BaseModel):
    to_email: EmailStr
    patient_name: str
    doctor_name: str
    appointment_time: datetime
    location: Optional[str] = None


class AppointmentReminderRequest(BaseModel):
    to_email: EmailStr
    patient_name: str
    doctor_name: str
    appointment_time: datetime
    hours_before: Optional[int] = None


class AppointmentCancellationRequest(BaseModel):
    to_email: EmailStr
    patient_name: str
    doctor_name: str
    appointment_time: datetime
    reason: Optional[str] = None


class AppointmentRescheduleRequest(BaseModel):
    to_email: EmailStr
    patient_name: str
    doctor_name: str
    old_time: datetime
    new_time: datetime


class MedicationReminderRequest(BaseModel):
    to_email: EmailStr
    patient_name: str
    medicine: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints — each returns 202 Accepted since the email itself sends
# asynchronously after the response
# ---------------------------------------------------------------------------

@router.post("/appointment-confirmation", status_code=status.HTTP_202_ACCEPTED)
def appointment_confirmation(data: AppointmentConfirmationRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        email_service.send_appointment_confirmation,
        to_email=data.to_email,
        patient_name=data.patient_name,
        doctor_name=data.doctor_name,
        appointment_time=data.appointment_time,
        location=data.location,
    )
    return {"message": "Appointment confirmation email queued"}


@router.post("/appointment-reminder", status_code=status.HTTP_202_ACCEPTED)
def appointment_reminder(data: AppointmentReminderRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        email_service.send_appointment_reminder,
        to_email=data.to_email,
        patient_name=data.patient_name,
        doctor_name=data.doctor_name,
        appointment_time=data.appointment_time,
        hours_before=data.hours_before,
    )
    return {"message": "Appointment reminder email queued"}


@router.post("/appointment-cancellation", status_code=status.HTTP_202_ACCEPTED)
def appointment_cancellation(data: AppointmentCancellationRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        email_service.send_appointment_cancellation,
        to_email=data.to_email,
        patient_name=data.patient_name,
        doctor_name=data.doctor_name,
        appointment_time=data.appointment_time,
        reason=data.reason,
    )
    return {"message": "Appointment cancellation email queued"}


@router.post("/appointment-reschedule", status_code=status.HTTP_202_ACCEPTED)
def appointment_reschedule(data: AppointmentRescheduleRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        email_service.send_appointment_reschedule,
        to_email=data.to_email,
        patient_name=data.patient_name,
        doctor_name=data.doctor_name,
        old_time=data.old_time,
        new_time=data.new_time,
    )
    return {"message": "Appointment reschedule email queued"}


@router.post("/medication-reminder", status_code=status.HTTP_202_ACCEPTED)
def medication_reminder(data: MedicationReminderRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        email_service.send_medication_reminder,
        to_email=data.to_email,
        patient_name=data.patient_name,
        medicine=data.medicine,
        dosage=data.dosage,
        frequency=data.frequency,
    )
    return {"message": "Medication reminder email queued"}
