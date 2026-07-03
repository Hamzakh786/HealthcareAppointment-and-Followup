from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.google_calendar import GoogleCalendarCredential, AppointmentCalendarSync, SyncStatus


class GoogleCredentialDBService:

    @staticmethod
    def get_by_user(db: Session, user_id: int) -> Optional[GoogleCalendarCredential]:
        return db.query(GoogleCalendarCredential).filter(
            GoogleCalendarCredential.user_id == user_id
        ).first()

    @staticmethod
    def upsert(
        db: Session,
        user_id: int,
        access_token: str,
        refresh_token: Optional[str],
        token_uri: str,
        client_id: str,
        client_secret: str,
        scopes: str,
        expiry: Optional[datetime],
    ) -> GoogleCalendarCredential:
        record = GoogleCredentialDBService.get_by_user(db, user_id)
        if record is None:
            record = GoogleCalendarCredential(user_id=user_id)
            db.add(record)

        record.access_token = access_token
        # A refresh may not return a new refresh_token — keep the old one if so
        if refresh_token:
            record.refresh_token = refresh_token
        record.token_uri = token_uri
        record.client_id = client_id
        record.client_secret = client_secret
        record.scopes = scopes
        record.expiry = expiry

        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def delete(db: Session, user_id: int) -> None:
        record = GoogleCredentialDBService.get_by_user(db, user_id)
        if record:
            db.delete(record)
            db.commit()


class CalendarSyncDBService:

    @staticmethod
    def get_by_appointment(db: Session, appointment_id: int) -> Optional[AppointmentCalendarSync]:
        return db.query(AppointmentCalendarSync).filter(
            AppointmentCalendarSync.appointment_id == appointment_id
        ).first()

    @staticmethod
    def upsert(
        db: Session,
        appointment_id: int,
        google_event_id: Optional[str],
        calendar_id: str,
        status: SyncStatus,
        error_message: Optional[str] = None,
    ) -> AppointmentCalendarSync:
        record = CalendarSyncDBService.get_by_appointment(db, appointment_id)
        if record is None:
            record = AppointmentCalendarSync(appointment_id=appointment_id)
            db.add(record)

        record.google_event_id = google_event_id
        record.calendar_id = calendar_id
        record.status = status
        record.error_message = error_message
        record.last_synced_at = datetime.utcnow() if status == SyncStatus.SYNCED else record.last_synced_at

        db.commit()
        db.refresh(record)
        return record
