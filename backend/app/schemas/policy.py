from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PolicyDocumentStatus


class PolicyDocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    status: PolicyDocumentStatus = PolicyDocumentStatus.draft


class PolicyDocumentCreate(PolicyDocumentBase):
    pass


class PolicyDocumentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(None, min_length=1, max_length=512)
    status: PolicyDocumentStatus | None = None
    current_version_id: int | None = None


class PolicyDocumentRead(PolicyDocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    current_version_id: int | None
    created_at: datetime
    updated_at: datetime


class PolicyVersionBase(BaseModel):
    version_number: int = Field(..., ge=1)
    content_markdown: str = Field(..., min_length=1)
    content_html: str | None = None
    generated_from_analysis: dict[str, Any] | None = None
    change_summary: str | None = Field(None, max_length=1024)


class PolicyVersionCreate(PolicyVersionBase):
    policy_document_id: int


class PolicyVersionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_markdown: str | None = Field(None, min_length=1)
    content_html: str | None = None
    generated_from_analysis: dict[str, Any] | None = None
    change_summary: str | None = Field(None, max_length=1024)


class PolicyVersionRead(PolicyVersionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_document_id: int
    created_at: datetime
    source_hash: str | None = None
    snapshot: dict[str, Any] | None = None


class PolicyVersionSummaryRead(BaseModel):
    """Версия без тяжёлого snapshot (список)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_document_id: int
    version_number: int
    source_hash: str | None = None
    change_summary: str | None = None
    created_at: datetime


class DiffChunk(BaseModel):
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    changed: list[str] = Field(default_factory=list)


class PolicySnapshotDiff(BaseModel):
    """Сравнение снимков по разделам assets / risks / measures."""

    assets: DiffChunk
    risks: DiffChunk
    measures: DiffChunk


class QuestionnairePolicyVersioningInfo(BaseModel):
    """Результат попытки записи версии при генерации политики."""

    status: str = Field(..., description="skipped | unchanged | created")
    version_id: int | None = None
    version_number: int | None = None
    source_hash: str | None = None


class QuestionnairePolicyGenerateResponse(BaseModel):
    """Ответ POST /questionnaires/{id}/generate-policy."""

    html_preview: str = Field(..., description="HTML предпросмотр документа")
    download_url: str = Field(
        ...,
        description="URL для скачивания DOCX (GET с тем же questionnaire_id)",
    )
    versioning: QuestionnairePolicyVersioningInfo | None = Field(
        None,
        description="Если передан policy_document_id — статус записи версии",
    )
