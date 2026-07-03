
"""
Doctor routes: create, get, update, delete, and search-by-specialization.

Access rules:
  - Create / Delete   -> ADMIN only
  - Update            -> ADMIN, or the DOCTOR who owns the profile
  - Get / Search       -> any authenticated user
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import RoleChecker, get_current_user
from app.models.doctor import Doctor
from app.models.user import RoleEnum, User
from app.schemas.doctor import (
    DoctorCreate,
    DoctorListResponse,
    DoctorResponse,
    DoctorUpdate,
)
from app.services.doctor_service import DoctorService

router = APIRouter(prefix="/doctors", tags=["Doctors"])


def _ensure_admin_or_owner(current_user: User, doctor: Doctor) -> None:
    is_owner = current_user.role == RoleEnum.DOCTOR and current_user.id == doctor.user_id
    is_admin = current_user.role == RoleEnum.ADMIN
    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this doctor profile.",
        )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=DoctorResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([RoleEnum.ADMIN]))],
)
def create_doctor(payload: DoctorCreate, db: Session = Depends(get_db)):
    """Create a doctor profile for an existing DOCTOR-role user. Admin only."""
    return DoctorService.create_doctor(db, payload)


# ---------------------------------------------------------------------------
# Search by specialization  (declared before /{doctor_id} to avoid route clash)
# ---------------------------------------------------------------------------
@router.get("/search", response_model=DoctorListResponse)
def search_doctors_by_specialization(
    specialization: str = Query(..., min_length=2, description="Specialization keyword"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search available (not on leave) doctors by specialization (partial, case-insensitive match)."""
    results = DoctorService.search_by_specialization(db, specialization, skip, limit)
    total = DoctorService.count_by_specialization(db, specialization)
    return DoctorListResponse(total=total, results=results)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
@router.get("", response_model=DoctorListResponse)
def list_doctors(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all doctor profiles (paginated)."""
    results = DoctorService.list_doctors(db, skip, limit)
    total = db.query(Doctor).count()
    return DoctorListResponse(total=total, results=results)


# ---------------------------------------------------------------------------
# Get by id
# ---------------------------------------------------------------------------
@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(
    doctor_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch a single doctor profile by doctor_id."""
    return DoctorService.get_doctor_by_id(db, doctor_id)


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------
@router.put("/{doctor_id}", response_model=DoctorResponse)
def update_doctor(
    doctor_id: uuid.UUID,
    payload: DoctorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a doctor profile. Allowed for ADMIN or the doctor who owns the profile."""
    doctor = DoctorService.get_doctor_by_id(db, doctor_id)
    _ensure_admin_or_owner(current_user, doctor)
    return DoctorService.update_doctor(db, doctor_id, payload)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
@router.delete(
    "/{doctor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([RoleEnum.ADMIN]))],
)
def delete_doctor(doctor_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a doctor profile. Admin only."""
    DoctorService.delete_doctor(db, doctor_id)
    return None
