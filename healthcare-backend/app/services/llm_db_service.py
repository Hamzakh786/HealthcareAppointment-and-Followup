from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.llm_response import LLMResponse, LLMResponseType, LLMResponseStatus


class LLMDBService:
    """Persists LLM generations (input + output JSON) to PostgreSQL via JSONB columns."""

    @staticmethod
    def create_response(
        db: Session,
        response_type: LLMResponseType,
        input_data: dict,
        result: dict,
        appointment_id: Optional[int] = None,
        prescription_id: Optional[int] = None,
        model_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
    ) -> LLMResponse:
        record = LLMResponse(
            response_type=response_type,
            appointment_id=appointment_id,
            prescription_id=prescription_id,
            input_data=input_data,
            output_data=result.get("data"),
            status=LLMResponseStatus.SUCCESS if result.get("success") else LLMResponseStatus.ERROR,
            error_message=result.get("error"),
            model_name=model_name,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_response(db: Session, response_id: int) -> LLMResponse:
        record = db.query(LLMResponse).filter(LLMResponse.id == response_id).first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"LLM response with id {response_id} not found",
            )
        return record

    @staticmethod
    def list_responses(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        response_type: Optional[LLMResponseType] = None,
        appointment_id: Optional[int] = None,
        prescription_id: Optional[int] = None,
    ) -> List[LLMResponse]:
        query = db.query(LLMResponse)
        if response_type is not None:
            query = query.filter(LLMResponse.response_type == response_type)
        if appointment_id is not None:
            query = query.filter(LLMResponse.appointment_id == appointment_id)
        if prescription_id is not None:
            query = query.filter(LLMResponse.prescription_id == prescription_id)
        return query.order_by(LLMResponse.created_at.desc()).offset(skip).limit(limit).all()
