from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import QuestionnaireStatus


class QuestionnaireBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    status: QuestionnaireStatus = QuestionnaireStatus.draft


class QuestionnaireCreate(QuestionnaireBase):
    department_id: int


class QuestionnaireUpdate(BaseModel):
    """Метаданные анкеты. Статус и submitted_at меняются только через workflow endpoints."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(None, min_length=1, max_length=512)


class QuestionnaireRead(QuestionnaireBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
