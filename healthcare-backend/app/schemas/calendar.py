from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.google_calendar import SyncStatus


class EventCreateRequest(BaseModel):
    user_id: int = Field(..., description="Doctor/staff user ID whose calendar to use")
    summary: str = Field(..., description="Event title")
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendee_emails: Optional[List[EmailStr]] = None
    location: Optional[str] = None
    calendar_id: str = "primary"


class EventUpdateRequest(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    attendee_emails: Optional[List[EmailStr]] = None
    location: Optional[str] = None
    calendar_id: str = "primary"


class EventResponse(BaseModel):
    event_id: str
    html_link: Optional[str] = None
    summary: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str


class SyncResponse(BaseModel):
    appointment_id: int
    google_event_id: Optional[str] = None
    status: SyncStatus
    message: str
