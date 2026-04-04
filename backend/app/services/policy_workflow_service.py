"""
MVP state-machine согласования политики: workflow_status + workflow_log в response_data.
Синхронизация с questionnaire.status (draft / submitted / needs_revision / approved).
"""

from __future__ import annotations

import copy
import logging
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.models.enums import QuestionnaireStatus
from app.models.questionnaire import Questionnaire
from app.models.questionnaire_response import QuestionnaireResponse
from app.schemas.policy_workflow import (
    QuestionnaireWorkflowStateRead,
    WorkflowAction,
    WorkflowActionRequest,
    WorkflowActionResponse,
    WorkflowLogEntry,
    WorkflowRole,
    WorkflowStatus,
)
from app.services.questionnaire_service import get_questionnaire

logger = logging.getLogger(__name__)

_WORKFLOW_STATUSES: frozenset[str] = frozenset(
    {"draft", "analyzed", "under_review", "approved", "needs_revision"},
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_rd(row: QuestionnaireResponse | None) -> dict[str, Any]:
    if row is None or not isinstance(row.response_data, dict):
        return {}
    return dict(row.response_data)


def effective_workflow_status(q: Questionnaire, rd: dict[str, Any]) -> WorkflowStatus:
    ws = rd.get("workflow_status")
    if isinstance(ws, str) and ws in _WORKFLOW_STATUSES:
        return ws  # type: ignore[return-value]
    if q.status == QuestionnaireStatus.approved:
        return "approved"
    if q.status == QuestionnaireStatus.needs_revision:
        return "needs_revision"
    if q.status == QuestionnaireStatus.submitted:
        return "under_review"
    ar = rd.get("analysis_result")
    if isinstance(ar, dict) and ar:
        return "analyzed"
    return "draft"


def parse_workflow_log(rd: dict[str, Any]) -> list[WorkflowLogEntry]:
    raw = rd.get("workflow_log")
    if not isinstance(raw, list):
        return []
    out: list[WorkflowLogEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            out.append(WorkflowLogEntry.model_validate(item))
        except Exception:  # noqa: BLE001
            continue
    return out


def _has_non_empty_analysis(rd: dict[str, Any]) -> bool:
    ar = rd.get("analysis_result")
    return isinstance(ar, dict) and bool(ar)


def _analysis_stale(rd: dict[str, Any]) -> bool:
    return rd.get("analysis_stale") is True


def allowed_workflow_actions(
    status: WorkflowStatus,
    role: WorkflowRole | None,
) -> list[WorkflowAction]:
    if role == "department_head":
        return []
    if role == "security_analyst":
        if status == "analyzed":
            return ["submit_for_review"]
        if status == "needs_revision":
            return ["revise"]
        return []
    if role == "approver":
        if status == "under_review":
            return ["approve", "reject"]
        return []
    return []


def get_workflow_state(
    db: Session,
    questionnaire_id: int,
    *,
    for_role: WorkflowRole | None = None,
) -> tuple[Literal["ok", "questionnaire_not_found", "response_not_found"], QuestionnaireWorkflowStateRead | None]:
    from app.services import questionnaire_collection_service as qc

    q = get_questionnaire(db, questionnaire_id)
    if q is None:
        return "questionnaire_not_found", None
    outcome, row, _ = qc.get_questionnaire_response(db, questionnaire_id)
    if outcome != "ok" or row is None:
        return "response_not_found", None
    rd = _as_rd(row)
    wfs = effective_workflow_status(q, rd)
    fb = rd.get("revision_feedback")
    rev = fb if isinstance(fb, str) and fb.strip() else None
    body = QuestionnaireWorkflowStateRead(
        workflow_status=wfs,
        questionnaire_status=q.status,
        workflow_log=parse_workflow_log(rd),
        analysis_stale=_analysis_stale(rd),
        has_analysis=_has_non_empty_analysis(rd),
        revision_feedback=rev,
        allowed_actions=allowed_workflow_actions(wfs, for_role),
    )
    return "ok", body


def _append_log(
    rd: dict[str, Any],
    *,
    action: str,
    from_status: str,
    to_status: str,
    actor: str,
    role: str,
    comment: str,
) -> None:
    log_raw = rd.get("workflow_log")
    log: list[Any] = copy.deepcopy(log_raw) if isinstance(log_raw, list) else []
    log.append(
        {
            "timestamp": _utc_iso(),
            "action": action,
            "from_status": from_status,
            "to_status": to_status,
            "actor": actor,
            "role": role,
            "comment": (comment or "").strip(),
        },
    )
    rd["workflow_log"] = log


def apply_workflow_action(
    db: Session,
    questionnaire_id: int,
    body: WorkflowActionRequest,
) -> tuple[Literal["ok", "questionnaire_not_found", "response_not_found", "forbidden", "invalid"], list[str], WorkflowActionResponse | None]:
    from app.services import questionnaire_collection_service as qc

    q = get_questionnaire(db, questionnaire_id)
    if q is None:
        return "questionnaire_not_found", [], None
    outcome, row, _ = qc.get_questionnaire_response(db, questionnaire_id)
    if outcome != "ok" or row is None:
        return "response_not_found", [], None

    if body.role == "department_head":
        return "forbidden", ["department_head cannot perform workflow actions in MVP"], None

    rd = _as_rd(row)
    current = effective_workflow_status(q, rd)
    comment = (body.comment or "").strip()

    if body.action == "submit_for_review":
        if body.role != "security_analyst":
            return "forbidden", ["submit_for_review requires role security_analyst"], None
        if current != "analyzed":
            return "invalid", [f"submit_for_review only from analyzed, now {current}"], None
        if not _has_non_empty_analysis(rd):
            return "invalid", ["Cannot submit for review without analysis_result"], None
        if _analysis_stale(rd):
            return "invalid", ["analysis_stale is true; re-run analyze before submit"], None
        _append_log(
            rd,
            action="submit_for_review",
            from_status=current,
            to_status="under_review",
            actor=body.actor,
            role=body.role,
            comment=comment,
        )
        rd["workflow_status"] = "under_review"
        q.status = QuestionnaireStatus.submitted
        if q.submitted_at is None:
            q.submitted_at = datetime.now(timezone.utc)

    elif body.action == "approve":
        if body.role != "approver":
            return "forbidden", ["approve requires role approver"], None
        if current != "under_review":
            return "invalid", [f"approve only from under_review, now {current}"], None
        _append_log(
            rd,
            action="approve",
            from_status=current,
            to_status="approved",
            actor=body.actor,
            role=body.role,
            comment=comment,
        )
        rd["workflow_status"] = "approved"
        q.status = QuestionnaireStatus.approved

    elif body.action == "reject":
        if body.role != "approver":
            return "forbidden", ["reject requires role approver"], None
        if current != "under_review":
            return "invalid", [f"reject only from under_review, now {current}"], None
        _append_log(
            rd,
            action="reject",
            from_status=current,
            to_status="needs_revision",
            actor=body.actor,
            role=body.role,
            comment=comment,
        )
        rd["workflow_status"] = "needs_revision"
        q.status = QuestionnaireStatus.needs_revision
        rd["revision_feedback"] = comment or "Возврат на доработку"

    elif body.action == "revise":
        if body.role != "security_analyst":
            return "forbidden", ["revise requires role security_analyst"], None
        if current != "needs_revision":
            return "invalid", [f"revise only from needs_revision, now {current}"], None
        _append_log(
            rd,
            action="revise",
            from_status=current,
            to_status="draft",
            actor=body.actor,
            role=body.role,
            comment=comment,
        )
        rd["workflow_status"] = "draft"
        q.status = QuestionnaireStatus.draft
        q.submitted_at = None
        if "revision_feedback" in rd:
            del rd["revision_feedback"]

    row.response_data = rd
    db.add(row)
    db.add(q)
    db.commit()
    db.refresh(row)
    db.refresh(q)

    new_rd = _as_rd(row)
    wfs = effective_workflow_status(q, new_rd)
    resp = WorkflowActionResponse(
        workflow_status=wfs,
        questionnaire_status=q.status,
        workflow_log=parse_workflow_log(new_rd),
        message=f"Workflow action {body.action} applied",
    )
    return "ok", [], resp


def merge_workflow_fields_into_stored(
    stored: dict[str, Any],
    existing_rd: dict[str, Any] | None,
) -> None:
    """Сохранить workflow при PUT /response (как analysis_result)."""
    if not existing_rd:
        return
    for key in ("workflow_status", "workflow_log"):
        if key in existing_rd:
            stored[key] = copy.deepcopy(existing_rd[key])


def transition_after_analyze(
    q: Questionnaire,
    old_rd: dict[str, Any],
    new_rd: dict[str, Any],
    *,
    actor: str = "system",
) -> None:
    """
    После успешного анализа: draft | needs_revision → analyzed + запись в лог.
    under_review / approved не трогаем.
    """
    eff_before = effective_workflow_status(q, old_rd)
    if eff_before not in ("draft", "needs_revision"):
        if isinstance(new_rd.get("workflow_status"), str) and new_rd["workflow_status"] in _WORKFLOW_STATUSES:
            return
        if eff_before == "analyzed":
            new_rd.setdefault("workflow_status", "analyzed")
        return

    new_rd["workflow_status"] = "analyzed"
    log_raw = old_rd.get("workflow_log")
    log: list[Any] = copy.deepcopy(log_raw) if isinstance(log_raw, list) else []
    log.append(
        {
            "timestamp": _utc_iso(),
            "action": "analysis_completed",
            "from_status": eff_before,
            "to_status": "analyzed",
            "actor": actor,
            "role": "security_analyst",
            "comment": "Анализ выполнен (rule-based / AI)",
        },
    )
    new_rd["workflow_log"] = log
