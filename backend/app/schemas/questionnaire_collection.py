from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import QuestionnaireStatus, ValidationStatus
from app.schemas.questionnaire_response_data import QuestionnaireResponseDataPayload


class QuestionnaireResponseSave(BaseModel):
    """Тело PUT /questionnaires/{id}/response."""

    response_data: QuestionnaireResponseDataPayload


class QuestionnaireResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    questionnaire_id: int
    response_data: dict[str, Any]
    validation_status: ValidationStatus
    validation_errors: dict[str, Any] | list[Any] | None
    created_at: datetime
    updated_at: datetime


class QuestionnaireStatusChangeResponse(BaseModel):
    questionnaire_id: int
    status: QuestionnaireStatus
    message: str


class QuestionnaireRevisionRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=8000)
