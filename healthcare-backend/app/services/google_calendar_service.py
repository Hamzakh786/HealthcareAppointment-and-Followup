"""
google_calendar_service.py

Handles:
    - OAuth2 authorization (auth URL generation + code exchange)
    - Loading/refreshing stored credentials per user
    - Create / Update / Delete calendar events
    - Synchronizing a local Appointment record with its Google Calendar event

Design notes:
    - Credentials (access + refresh tokens) are persisted per user in
      GoogleCalendarCredential so users authorize once, not per request.
    - Every API call refreshes the token first if it's expired, and
      persists the refreshed token back to the DB.
    - All Google API failures (auth errors, HTTP errors, network errors)
      are caught and converted into the module's own exception types so
      callers never have to import/handle google's exception classes.
"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.google_config import google_settings
from app.models.google_calendar import SyncStatus
from app.services.calendar_db_service import GoogleCredentialDBService, CalendarSyncDBService

logger = logging.getLogger(__name__)


class GoogleAuthError(Exception):
    """Raised when OAuth authorization or token refresh fails."""


class GoogleCalendarAPIError(Exception):
    """Raised when a Calendar API call (create/update/delete) fails."""


# ---------------------------------------------------------------------------
# OAuth2
# ---------------------------------------------------------------------------

def get_authorization_url(user_id: int) -> str:
    """
    Build the Google consent screen URL. `user_id` is embedded in `state`
    so the callback knows which local user to attach the resulting tokens to.
    """
    try:
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            google_settings.client_config,
            scopes=google_settings.SCOPES,
            redirect_uri=google_settings.REDIRECT_URI,
        )
        auth_url, _state = flow.authorization_url(
            access_type="offline",       # required to get a refresh_token
            include_granted_scopes="true",
            prompt="consent",            # forces refresh_token on repeat auth
            state=str(user_id),
        )
        return auth_url
    except Exception as exc:
        logger.exception("Failed to build Google authorization URL")
        raise GoogleAuthError(f"Failed to build authorization URL: {exc}") from exc


def exchange_code_for_tokens(db: Session, code: str, state: str) -> int:
    """
    Exchange the OAuth `code` from the callback for tokens and persist them.
    Returns the user_id the tokens were attached to (parsed from `state`).
    """
    try:
        user_id = int(state)
    except (TypeError, ValueError) as exc:
        raise GoogleAuthError(f"Invalid state parameter: {state}") from exc

    try:
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            google_settings.client_config,
            scopes=google_settings.SCOPES,
            redirect_uri=google_settings.REDIRECT_URI,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials

        GoogleCredentialDBService.upsert(
            db,
            user_id=user_id,
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            token_uri=creds.token_uri,
            client_id=creds.client_id,
            client_secret=creds.client_secret,
            scopes=" ".join(creds.scopes or google_settings.SCOPES),
            expiry=creds.expiry,
        )
        return user_id

    except GoogleAuthError:
        raise
    except Exception as exc:
        logger.exception("Failed to exchange authorization code for tokens")
        raise GoogleAuthError(f"Failed to exchange code for tokens: {exc}") from exc


def _get_credentials(db: Session, user_id: int):
    """
    Load stored credentials for a user, refreshing the access token if
    expired, and persisting the refreshed token back to the DB.
    Raises GoogleAuthError if the user hasn't authorized, or if the
    refresh token has been revoked/expired (requires re-authorization).
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError

    record = GoogleCredentialDBService.get_by_user(db, user_id)
    if record is None:
        raise GoogleAuthError(
            f"No Google Calendar authorization found for user {user_id}. "
            f"Visit /google-calendar/auth/login?user_id={user_id} first."
        )

    creds = Credentials(
        token=record.access_token,
        refresh_token=record.refresh_token,
        token_uri=record.token_uri,
        client_id=record.client_id,
        client_secret=record.client_secret,
        scopes=record.scopes.split(" "),
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            GoogleCredentialDBService.upsert(
                db,
                user_id=user_id,
                access_token=creds.token,
                refresh_token=creds.refresh_token,
                token_uri=creds.token_uri,
                client_id=creds.client_id,
                client_secret=creds.client_secret,
                scopes=" ".join(creds.scopes or []),
                expiry=creds.expiry,
            )
        except RefreshError as exc:
            logger.warning("Token refresh failed for user %s: %s", user_id, exc)
            raise GoogleAuthError(
                f"Google Calendar authorization for user {user_id} has expired or "
                f"been revoked. Re-authorize via /google-calendar/auth/login?user_id={user_id}."
            ) from exc

    return creds


def _build_service(db: Session, user_id: int):
    from googleapiclient.discovery import build

    creds = _get_credentials(db, user_id)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


# ---------------------------------------------------------------------------
# Event CRUD
# ---------------------------------------------------------------------------

def _build_event_body(
    summary: str,
    description: Optional[str],
    start_time: datetime,
    end_time: datetime,
    attendee_emails: Optional[List[str]],
    location: Optional[str],
) -> dict:
    body = {
        "summary": summary,
        "description": description or "",
        "start": {"dateTime": start_time.isoformat(), "timeZone": google_settings.DEFAULT_TIMEZONE},
        "end": {"dateTime": end_time.isoformat(), "timeZone": google_settings.DEFAULT_TIMEZONE},
    }
    if location:
        body["location"] = location
    if attendee_emails:
        body["attendees"] = [{"email": email} for email in attendee_emails]
    return body


def create_event(
    db: Session,
    user_id: int,
    summary: str,
    start_time: datetime,
    end_time: datetime,
    description: Optional[str] = None,
    attendee_emails: Optional[List[str]] = None,
    location: Optional[str] = None,
    calendar_id: str = "primary",
) -> dict:
    from googleapiclient.errors import HttpError

    try:
        service = _build_service(db, user_id)
        body = _build_event_body(summary, description, start_time, end_time, attendee_emails, location)
        event = service.events().insert(calendarId=calendar_id, body=body, sendUpdates="all").execute()
        logger.info("Created Google Calendar event %s for user %s", event.get("id"), user_id)
        return event

    except GoogleAuthError:
        raise
    except HttpError as exc:
        logger.exception("Google Calendar API error creating event")
        raise GoogleCalendarAPIError(f"Failed to create event: {exc}") from exc
    except Exception as exc:
        logger.exception("Unexpected error creating event")
        raise GoogleCalendarAPIError(f"Unexpected error creating event: {exc}") from exc


def update_event(
    db: Session,
    user_id: int,
    event_id: str,
    summary: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    description: Optional[str] = None,
    attendee_emails: Optional[List[str]] = None,
    location: Optional[str] = None,
    calendar_id: str = "primary",
) -> dict:
    from googleapiclient.errors import HttpError

    try:
        service = _build_service(db, user_id)

        existing = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        if summary is not None:
            existing["summary"] = summary
        if description is not None:
            existing["description"] = description
        if location is not None:
            existing["location"] = location
        if start_time is not None:
            existing["start"] = {"dateTime": start_time.isoformat(), "timeZone": google_settings.DEFAULT_TIMEZONE}
        if end_time is not None:
            existing["end"] = {"dateTime": end_time.isoformat(), "timeZone": google_settings.DEFAULT_TIMEZONE}
        if attendee_emails is not None:
            existing["attendees"] = [{"email": email} for email in attendee_emails]

        updated = service.events().update(
            calendarId=calendar_id, eventId=event_id, body=existing, sendUpdates="all"
        ).execute()
        logger.info("Updated Google Calendar event %s for user %s", event_id, user_id)
        return updated

    except GoogleAuthError:
        raise
    except HttpError as exc:
        logger.exception("Google Calendar API error updating event %s", event_id)
        raise GoogleCalendarAPIError(f"Failed to update event {event_id}: {exc}") from exc
    except Exception as exc:
        logger.exception("Unexpected error updating event %s", event_id)
        raise GoogleCalendarAPIError(f"Unexpected error updating event {event_id}: {exc}") from exc


def delete_event(
    db: Session,
    user_id: int,
    event_id: str,
    calendar_id: str = "primary",
) -> None:
    from googleapiclient.errors import HttpError

    try:
        service = _build_service(db, user_id)
        service.events().delete(calendarId=calendar_id, eventId=event_id, sendUpdates="all").execute()
        logger.info("Deleted Google Calendar event %s for user %s", event_id, user_id)

    except GoogleAuthError:
        raise
    except HttpError as exc:
        if exc.resp.status == 410:
            # Event was already deleted on Google's side — treat as success
            logger.info("Event %s already deleted on Google Calendar", event_id)
            return
        logger.exception("Google Calendar API error deleting event %s", event_id)
        raise GoogleCalendarAPIError(f"Failed to delete event {event_id}: {exc}") from exc
    except Exception as exc:
        logger.exception("Unexpected error deleting event %s", event_id)
        raise GoogleCalendarAPIError(f"Unexpected error deleting event {event_id}: {exc}") from exc


# ---------------------------------------------------------------------------
# Appointment synchronization
# ---------------------------------------------------------------------------

def synchronize_appointment(
    db: Session,
    user_id: int,
    appointment_id: int,
    summary: str,
    start_time: datetime,
    end_time: datetime,
    description: Optional[str] = None,
    attendee_emails: Optional[List[str]] = None,
    location: Optional[str] = None,
    calendar_id: str = "primary",
) -> dict:
    """
    Idempotent sync: creates a Google Calendar event for the appointment if
    none exists yet, otherwise updates the existing one. Tracks the mapping
    and status in AppointmentCalendarSync so repeated calls don't create
    duplicate events.

    Returns {"appointment_id", "google_event_id", "status", "message"}.
    Never raises — failures are captured in the returned/stored status so
    a sync failure for one appointment doesn't blow up a batch sync job.
    """
    sync_record = CalendarSyncDBService.get_by_appointment(db, appointment_id)

    try:
        if sync_record and sync_record.google_event_id and sync_record.status != SyncStatus.DELETED:
            event = update_event(
                db, user_id, sync_record.google_event_id,
                summary=summary, start_time=start_time, end_time=end_time,
                description=description, attendee_emails=attendee_emails,
                location=location, calendar_id=calendar_id,
            )
        else:
            event = create_event(
                db, user_id, summary, start_time, end_time,
                description=description, attendee_emails=attendee_emails,
                location=location, calendar_id=calendar_id,
            )

        updated_record = CalendarSyncDBService.upsert(
            db, appointment_id, event.get("id"), calendar_id, SyncStatus.SYNCED
        )
        return {
            "appointment_id": appointment_id,
            "google_event_id": updated_record.google_event_id,
            "status": SyncStatus.SYNCED,
            "message": "Appointment synced to Google Calendar",
        }

    except (GoogleAuthError, GoogleCalendarAPIError) as exc:
        CalendarSyncDBService.upsert(
            db, appointment_id,
            google_event_id=sync_record.google_event_id if sync_record else None,
            calendar_id=calendar_id, status=SyncStatus.FAILED, error_message=str(exc),
        )
        return {
            "appointment_id": appointment_id,
            "google_event_id": sync_record.google_event_id if sync_record else None,
            "status": SyncStatus.FAILED,
            "message": str(exc),
        }


def unsync_appointment(db: Session, user_id: int, appointment_id: int) -> dict:
    """Delete the Google Calendar event tied to an appointment (e.g. on cancellation)."""
    sync_record = CalendarSyncDBService.get_by_appointment(db, appointment_id)
    if not sync_record or not sync_record.google_event_id:
        return {"appointment_id": appointment_id, "google_event_id": None,
                "status": SyncStatus.DELETED, "message": "No linked event to delete"}

    try:
        delete_event(db, user_id, sync_record.google_event_id, sync_record.calendar_id)
        CalendarSyncDBService.upsert(
            db, appointment_id, sync_record.google_event_id, sync_record.calendar_id, SyncStatus.DELETED
        )
        return {"appointment_id": appointment_id, "google_event_id": sync_record.google_event_id,
                "status": SyncStatus.DELETED, "message": "Event deleted from Google Calendar"}

    except (GoogleAuthError, GoogleCalendarAPIError) as exc:
        CalendarSyncDBService.upsert(
            db, appointment_id, sync_record.google_event_id, sync_record.calendar_id,
            SyncStatus.FAILED, error_message=str(exc),
        )
        return {"appointment_id": appointment_id, "google_event_id": sync_record.google_event_id,
                "status": SyncStatus.FAILED, "message": str(exc)}
