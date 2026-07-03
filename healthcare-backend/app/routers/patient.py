

"""
Patient routes: create, get, update, delete, list.

Access rules (medical data is sensitive, so access is deliberately tighter
than the Doctor module):
  - Create  -> ADMIN, or the PATIENT creating their own profile
  - Get     -> ADMIN, DOCTOR, or the PATIENT who owns the profile
  - List    -> ADMIN or DOCTOR only
  - Update  -> ADMIN, or the PATIENT who owns the profile
  - Delete  -> ADMIN only
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import RoleChecker, get_current_user
from app.models.patient import Patient
from app.models.user import RoleEnum, User
from app.schemas.patient import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)
from app.services.patient_service import PatientService
router = APIRouter(prefix="/patients", tags=["Patients"])


def _is_owner(current_user: User, patient: Patient) -> bool:
    return current_user.role == RoleEnum.PATIENT and current_user.id == patient.user_id


def _ensure_can_view(current_user: User, patient: Patient) -> None:
    if current_user.role in (RoleEnum.ADMIN, RoleEnum.DOCTOR) or _is_owner(
        current_user, patient
    ):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to view this patient profile.",
    )


def _ensure_can_modify(current_user: User, patient: Patient) -> None:
    if current_user.role == RoleEnum.ADMIN or _is_owner(current_user, patient):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to modify this patient profile.",
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a patient profile. Admins can create for any user; patients may only
    create their own profile (payload.user_id must match their own account)."""
    if current_user.role not in (RoleEnum.ADMIN, RoleEnum.PATIENT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or the patient themselves can create this profile.",
        )
    if current_user.role == RoleEnum.PATIENT and current_user.id != payload.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients may only create their own profile.",
        )
    return PatientService.create_patient(db, payload)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=PatientListResponse,
    dependencies=[Depends(RoleChecker([RoleEnum.ADMIN, RoleEnum.DOCTOR]))],
)
def list_patients(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all patient profiles (paginated). Admin/Doctor only."""
    results = PatientService.list_patients(db, skip, limit)
    total = db.query(Patient).count()
    return PatientListResponse(total=total, results=results)


# ---------------------------------------------------------------------------
# Get by id
# ---------------------------------------------------------------------------
@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch a single patient profile. Admin, Doctor, or the owning Patient."""
    patient = PatientService.get_patient_by_id(db, patient_id)
    _ensure_can_view(current_user, patient)
    return patient


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------
@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: uuid.UUID,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a patient profile. Admin or the owning Patient only."""
    patient = PatientService.get_patient_by_id(db, patient_id)
    _ensure_can_modify(current_user, patient)
    return PatientService.update_patient(db, patient_id, payload)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([RoleEnum.ADMIN]))],
)
def delete_patient(patient_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a patient profile. Admin only."""
    PatientService.delete_patient(db, patient_id)
    return None
