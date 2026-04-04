"""MVP workflow согласования политики ИБ (без BPM и ЭЦП)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import QuestionnaireStatus

WorkflowStatus = Literal["draft", "analyzed", "under_review", "approved", "needs_revision"]

WorkflowRole = Literal["security_analyst", "department_head", "approver"]

WorkflowAction = Literal["submit_for_review", "approve", "reject", "revise"]


class WorkflowLogEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    timestamp: str
    action: str
    from_status: str
    to_status: str
    actor: str = "anonymous"
    role: str = ""
    comment: str = ""


class QuestionnaireWorkflowStateRead(BaseModel):
    """GET /questionnaires/{id}/workflow"""

    workflow_status: WorkflowStatus
    questionnaire_status: QuestionnaireStatus
    workflow_log: list[WorkflowLogEntry] = Field(default_factory=list)
    analysis_stale: bool = False
    has_analysis: bool = False
    revision_feedback: str | None = None
    allowed_actions: list[WorkflowAction] = Field(default_factory=list)


class WorkflowActionRequest(BaseModel):
    """POST /questionnaires/{id}/workflow/action"""

    action: WorkflowAction
    comment: str = ""
    actor: str = Field(default="anonymous", min_length=1, max_length=256)
    role: WorkflowRole


class WorkflowActionResponse(BaseModel):
    workflow_status: WorkflowStatus
    questionnaire_status: QuestionnaireStatus
    workflow_log: list[WorkflowLogEntry] = Field(default_factory=list)
    message: str = ""
