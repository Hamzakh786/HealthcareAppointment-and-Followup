import enum

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class LLMResponseType(str, enum.Enum):
    PRE_VISIT_SUMMARY = "pre_visit_summary"
    POST_VISIT_SUMMARY = "post_visit_summary"
    PRESCRIPTION_EXPLANATION = "prescription_explanation"


class LLMResponseStatus(str, enum.Enum):
    SUCCESS = "success"
    ERROR = "error"


class LLMResponse(Base):
    """
    Stores every LLM generation (input + structured JSON output) for audit,
    caching, and display purposes.

    input_data / output_data use PostgreSQL JSONB so they can be queried
    and indexed natively (e.g. `output_data ->> 'diagnosis'`).
    """

    __tablename__ = "llm_responses"

    id = Column(Integer, primary_key=True, index=True)

    response_type = Column(
        SQLEnum(LLMResponseType, name="llm_response_type"), nullable=False, index=True
    )

    # Optional linkage to other domain records — set whichever is relevant
    appointment_id = Column(Integer, nullable=True, index=True)
    prescription_id = Column(Integer, nullable=True, index=True)

    input_data = Column(JSONB, nullable=False)
    output_data = Column(JSONB, nullable=True)  # null when generation failed

    status = Column(
        SQLEnum(LLMResponseStatus, name="llm_response_status"),
        nullable=False,
        default=LLMResponseStatus.SUCCESS,
        index=True,
    )
    error_message = Column(String(1000), nullable=True)

    model_name = Column(String(255), nullable=False, default="Qwen/Qwen2.5-1.5B-Instruct")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<LLMResponse id={self.id} type={self.response_type} status={self.status}>"
