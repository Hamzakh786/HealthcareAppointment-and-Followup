"""
Patient business logic: CRUD operations.
"""
import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.user import RoleEnum, User
from app.schemas.patient import PatientCreate, PatientUpdate


class PatientService:
    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------
    @staticmethod
    def get_patient_by_id(db: Session, patient_id: uuid.UUID) -> Patient:
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found.",
            )
        return patient

    @staticmethod
    def get_patient_by_user_id(db: Session, user_id: uuid.UUID) -> Optional[Patient]:
        return db.query(Patient).filter(Patient.user_id == user_id).first()

    @staticmethod
    def list_patients(db: Session, skip: int = 0, limit: int = 20) -> List[Patient]:
        return db.query(Patient).offset(skip).limit(limit).all()

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    @staticmethod
    def create_patient(db: Session, payload: PatientCreate) -> Patient:
        user = db.query(User).filter(User.id == payload.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No user found with the given user_id.",
            )
        if user.role != RoleEnum.PATIENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The linked user account must have the PATIENT role.",
            )
        if PatientService.get_patient_by_user_id(db, payload.user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A patient profile already exists for this user.",
            )

        new_patient = Patient(
            patient_id=uuid.uuid4(),
            user_id=payload.user_id,
            age=payload.age,
            gender=payload.gender,
            phone=payload.phone,
            address=payload.address,
            blood_group=payload.blood_group,
            medical_history=payload.medical_history,
        )

        db.add(new_patient)
        try:
            db.commit()
            db.refresh(new_patient)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A patient profile already exists for this user.",
            )
        return new_patient

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    @staticmethod
    def update_patient(
        db: Session, patient_id: uuid.UUID, payload: PatientUpdate
    ) -> Patient:
        patient = PatientService.get_patient_by_id(db, patient_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(patient, field, value)

        db.commit()
        db.refresh(patient)
        return patient

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    @staticmethod
    def delete_patient(db: Session, patient_id: uuid.UUID) -> None:
        patient = PatientService.get_patient_by_id(db, patient_id)
        db.delete(patient)
        db.commit()
