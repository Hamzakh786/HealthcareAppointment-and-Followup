from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.llm_response import LLMResponseType
from app.schemas.llm_response import (
    PreVisitSummaryRequest,
    PostVisitSummaryRequest,
    PrescriptionExplanationRequest,
    LLMResponseOut,
)
from app.services.llm_service import (
    generate_pre_visit_summary,
    generate_post_visit_summary,
    generate_prescription_explanation,
    ModelManager,
    MODEL_NAME,
)
from app.services.llm_db_service import LLMDBService

router = APIRouter(prefix="/llm", tags=["AI / LLM"])


def _handle_generation(
    db: Session,
    response_type: LLMResponseType,
    input_data: dict,
    result: dict,
    appointment_id: Optional[int] = None,
    prescription_id: Optional[int] = None,
) -> LLMResponseOut:
    """
    Persists the generation attempt (success or failure) then either returns
    the structured result or raises a clean 502 with the stored record's ID
    for traceability.
    """
    record = LLMDBService.create_response(
        db, response_type, input_data, result,
        appointment_id=appointment_id, prescription_id=prescription_id,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "LLM generation failed",
                "error": result.get("error"),
                "response_id": record.id,
            },
        )
    return LLMResponseOut.model_validate(record)


@router.post(
    "/pre-visit-summary",
    response_model=LLMResponseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a pre-visit summary from patient-reported symptoms",
)
def pre_visit_summary(data: PreVisitSummaryRequest, db: Session = Depends(get_db)):
    payload = data.model_dump()
    result = generate_pre_visit_summary(payload)
    return _handle_generation(
        db, LLMResponseType.PRE_VISIT_SUMMARY, payload, result, appointment_id=data.appointment_id
    )


@router.post(
    "/post-visit-summary",
    response_model=LLMResponseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a patient-friendly post-visit summary from doctor notes",
)
def post_visit_summary(data: PostVisitSummaryRequest, db: Session = Depends(get_db)):
    payload = data.model_dump()
    result = generate_post_visit_summary(payload)
    return _handle_generation(
        db, LLMResponseType.POST_VISIT_SUMMARY, payload, result, appointment_id=data.appointment_id
    )


@router.post(
    "/prescription-explanation",
    response_model=LLMResponseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a plain-language explanation of a prescription",
)
def prescription_explanation(data: PrescriptionExplanationRequest, db: Session = Depends(get_db)):
    payload = data.model_dump()
    result = generate_prescription_explanation(payload)
    return _handle_generation(
        db, LLMResponseType.PRESCRIPTION_EXPLANATION, payload, result, prescription_id=data.prescription_id
    )


@router.get(
    "/responses/{response_id}",
    response_model=LLMResponseOut,
    summary="Fetch a previously stored LLM response by ID",
)
def get_response(response_id: int, db: Session = Depends(get_db)):
    return LLMDBService.get_response(db, response_id)


@router.get(
    "/responses",
    response_model=List[LLMResponseOut],
    summary="List stored LLM responses (filterable)",
)
def list_responses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    response_type: Optional[LLMResponseType] = None,
    appointment_id: Optional[int] = None,
    prescription_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return LLMDBService.list_responses(
        db, skip, limit, response_type, appointment_id, prescription_id
    )


@router.get("/health", summary="Check whether the LLM model is loaded and ready")
def health_check():
    manager = ModelManager.get_instance()
    return {
        "model_name": MODEL_NAME,
        "is_ready": manager.is_ready,
        "load_error": manager.load_error,
    }
