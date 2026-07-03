"""
Doctor business logic: CRUD operations and specialization search.
"""

import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.doctor import Doctor
from app.models.user import RoleEnum, User
from app.schemas.doctor import DoctorCreate, DoctorUpdate


class DoctorService:
    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------
    @staticmethod
    def get_doctor_by_id(db: Session, doctor_id: uuid.UUID) -> Doctor:
        doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found.",
            )
        return doctor

    @staticmethod
    def get_doctor_by_user_id(db: Session, user_id: uuid.UUID) -> Optional[Doctor]:
        return db.query(Doctor).filter(Doctor.user_id == user_id).first()

    @staticmethod
    def list_doctors(db: Session, skip: int = 0, limit: int = 20) -> List[Doctor]:
        return db.query(Doctor).offset(skip).limit(limit).all()

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    @staticmethod
    def create_doctor(db: Session, payload: DoctorCreate) -> Doctor:
        user = db.query(User).filter(User.id == payload.user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No user found with the given user_id.",
            )

        if user.role != RoleEnum.DOCTOR:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The linked user account must have the DOCTOR role.",
            )

        if DoctorService.get_doctor_by_user_id(db, payload.user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A doctor profile already exists for this user.",
            )

        new_doctor = Doctor(
            doctor_id=uuid.uuid4(),
            user_id=payload.user_id,
            specialization=payload.specialization,
            qualification=payload.qualification,
            experience=payload.experience,
            working_hours=payload.working_hours.model_dump(),
            slot_duration=payload.slot_duration,
            consultation_fee=payload.consultation_fee,
            leave_status=payload.leave_status,
        )

        db.add(new_doctor)

        try:
            db.commit()
            db.refresh(new_doctor)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A doctor profile already exists for this user.",
            )

        return new_doctor

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    @staticmethod
    def update_doctor(
        db: Session,
        doctor_id: uuid.UUID,
        payload: DoctorUpdate,
    ) -> Doctor:
        doctor = DoctorService.get_doctor_by_id(db, doctor_id)

        update_data = payload.model_dump(exclude_unset=True)

        if (
            "working_hours" in update_data
            and update_data["working_hours"] is not None
        ):
            update_data["working_hours"] = payload.working_hours.model_dump()

        for field, value in update_data.items():
            setattr(doctor, field, value)

        db.commit()
        db.refresh(doctor)

        return doctor

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    @staticmethod
    def delete_doctor(db: Session, doctor_id: uuid.UUID) -> None:
        doctor = DoctorService.get_doctor_by_id(db, doctor_id)
        db.delete(doctor)
        db.commit()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    @staticmethod
    def search_by_specialization(
        db: Session,
        specialization: str,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Doctor]:
        return (
            db.query(Doctor)
            .filter(func.lower(Doctor.specialization).contains(specialization.lower()))
            .filter(Doctor.leave_status.is_(False))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_by_specialization(
        db: Session,
        specialization: str,
    ) -> int:
        return (
            db.query(Doctor)
            .filter(func.lower(Doctor.specialization).contains(specialization.lower()))
            .filter(Doctor.leave_status.is_(False))
            .count()
        )