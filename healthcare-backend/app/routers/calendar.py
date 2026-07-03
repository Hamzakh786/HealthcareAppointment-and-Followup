from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.google_calendar import (
    EventCreateRequest,
    EventUpdateRequest,
    EventResponse,
    SyncResponse,
)
from app.services import google_calendar_service as gcal
from app.services.google_calendar_service import GoogleAuthError, GoogleCalendarAPIError

router = APIRouter(prefix="/google-calendar", tags=["Google Calendar"])


# ---------------------------------------------------------------------------
# OAuth2
# ---------------------------------------------------------------------------

@router.get("/auth/login", summary="Redirect the user to Google's OAuth consent screen")
def auth_login(user_id: int = Query(..., description="Local doctor/staff user ID authorizing their calendar")):
    try:
        auth_url = gcal.get_authorization_url(user_id)
    except GoogleAuthError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return RedirectResponse(auth_url)


@router.get("/auth/callback", summary="OAuth2 redirect URI — exchanges the code for tokens")
def auth_callback(code: str, state: str, db: Session = Depends(get_db)):
    try:
        user_id = gcal.exchange_code_for_tokens(db, code, state)
    except GoogleAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"message": "Google Calendar connected successfully", "user_id": user_id}


# ---------------------------------------------------------------------------
# Event CRUD
# ---------------------------------------------------------------------------

@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(data: EventCreateRequest, db: Session = Depends(get_db)):
    try:
        event = gcal.create_event(
            db, data.user_id, data.summary, data.start_time, data.end_time,
            description=data.description, attendee_emails=data.attendee_emails,
            location=data.location, calendar_id=data.calendar_id,
        )
    except GoogleAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except GoogleCalendarAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return _event_to_response(event)


@router.put("/events/{event_id}", response_model=EventResponse)
def update_event(
    event_id: str,
    data: EventUpdateRequest,
    user_id: int = Query(..., description="Doctor/staff user ID whose calendar owns this event"),
    db: Session = Depends(get_db),
):
    try:
        event = gcal.update_event(
            db, user_id, event_id,
            summary=data.summary, start_time=data.start_time, end_time=data.end_time,
            description=data.description, attendee_emails=data.attendee_emails,
            location=data.location, calendar_id=data.calendar_id,
        )
    except GoogleAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except GoogleCalendarAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return _event_to_response(event)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: str,
    user_id: int = Query(..., description="Doctor/staff user ID whose calendar owns this event"),
    calendar_id: str = Query("primary"),
    db: Session = Depends(get_db),
):
    try:
        gcal.delete_event(db, user_id, event_id, calendar_id)
    except GoogleAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except GoogleCalendarAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return None


# ---------------------------------------------------------------------------
# Appointment synchronization
# ---------------------------------------------------------------------------

@router.post("/sync/{appointment_id}", response_model=SyncResponse, summary="Create or update this appointment's Google Calendar event")
def sync_appointment(
    appointment_id: int,
    data: EventCreateRequest,
    db: Session = Depends(get_db),
):
    """
    `data` carries the appointment's current details (summary/time/attendees).
    In your real app you'd typically fetch these from the Appointment record
    itself rather than accepting them in the request body — see README.
    """
    result = gcal.synchronize_appointment(
        db, data.user_id, appointment_id, data.summary, data.start_time, data.end_time,
        description=data.description, attendee_emails=data.attendee_emails,
        location=data.location, calendar_id=data.calendar_id,
    )
    return result


@router.delete("/sync/{appointment_id}", response_model=SyncResponse, summary="Remove this appointment's Google Calendar event")
def unsync_appointment(
    appointment_id: int,
    user_id: int = Query(..., description="Doctor/staff user ID whose calendar owns the event"),
    db: Session = Depends(get_db),
):
    return gcal.unsync_appointment(db, user_id, appointment_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event_to_response(event: dict) -> EventResponse:
    return EventResponse(
        event_id=event.get("id"),
        html_link=event.get("htmlLink"),
        summary=event.get("summary", ""),
        start_time=event.get("start", {}).get("dateTime"),
        end_time=event.get("end", {}).get("dateTime"),
        status=event.get("status", "unknown"),
    )
