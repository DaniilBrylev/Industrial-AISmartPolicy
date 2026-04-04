from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import QuestionnaireStatus, ValidationStatus
from app.models.questionnaire import Questionnaire
from app.models.questionnaire_response import QuestionnaireResponse
from app.schemas.questionnaire_collection import QuestionnaireResponseSave
from app.schemas.questionnaire_response_data import (
    LIST_SECTION_KEYS,
    REQUIRED_TOP_LEVEL_KEYS,
    QuestionnaireResponseDataPayload,
)

from app.services.questionnaire_service import get_questionnaire

Outcome = Literal[
    "ok",
    "questionnaire_not_found",
    "response_not_found",
    "forbidden_approved",
    "forbidden_submitted",
    "invalid_transition",
    "validation_error",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def validate_response_structure(raw: Any) -> tuple[bool, list[str]]:
    """Базовая проверка структуры response_data (без правил submit)."""
    errors: list[str] = []
    if raw is None or not isinstance(raw, dict):
        return False, ["response_data must be a JSON object"]

    missing = REQUIRED_TOP_LEVEL_KEYS - set(raw.keys())
    if missing:
        errors.append(f"Missing required keys: {sorted(missing)}")

    dp = raw.get("department_profile")
    if dp is not None and not isinstance(dp, dict):
        errors.append("department_profile must be an object")

    for key in LIST_SECTION_KEYS:
        val = raw.get(key)
        if val is not None and not isinstance(val, list):
            errors.append(f"{key} must be an array")

    notes = raw.get("additional_notes")
    if notes is not None and not isinstance(notes, str):
        errors.append("additional_notes must be a string")

    if errors:
        return False, errors

    try:
        QuestionnaireResponseDataPayload.model_validate(raw)
    except Exception as e:  # noqa: BLE001 — учебный MVP
        errors.append(f"Invalid payload shape: {e}")
        return False, errors

    return True, []


def _profile_non_empty(profile: dict[str, Any]) -> bool:
    for k in ("description", "manager_name", "contact_info"):
        v = profile.get(k)
        if isinstance(v, str) and v.strip():
            return True
    return False


def validate_submit_ready(raw: Any) -> tuple[bool, list[str]]:
    ok, base_errs = validate_response_structure(raw)
    if not ok:
        return False, base_errs

    assert isinstance(raw, dict)
    errors: list[str] = []

    dp = raw.get("department_profile")
    if not isinstance(dp, dict) or not _profile_non_empty(dp):
        errors.append(
            "For submit, department_profile must be non-empty "
            "(at least one of description, manager_name, contact_info)"
        )

    assets = raw.get("assets")
    if not isinstance(assets, list) or len(assets) < 1:
        errors.append("For submit, assets must be a non-empty array")

    bp = raw.get("business_processes")
    if not isinstance(bp, list) or len(bp) < 1:
        errors.append("For submit, business_processes must be a non-empty array")

    return len(errors) == 0, errors


def _get_response_row(
    db: Session, questionnaire_id: int
) -> QuestionnaireResponse | None:
    return db.scalar(
        select(QuestionnaireResponse)
        .where(QuestionnaireResponse.questionnaire_id == questionnaire_id)
        .order_by(QuestionnaireResponse.id.asc())
        .limit(1)
    )


def _extract_revision_feedback(stored: dict[str, Any] | None) -> str | None:
    if not stored:
        return None
    fb = stored.get("revision_feedback")
    return fb if isinstance(fb, str) else None


def get_questionnaire_response(
    db: Session, questionnaire_id: int
) -> tuple[Outcome, QuestionnaireResponse | None, list[str]]:
    q = get_questionnaire(db, questionnaire_id)
    if q is None:
        return "questionnaire_not_found", None, []
    row = _get_response_row(db, questionnaire_id)
    if row is None:
        return "response_not_found", None, []
    return "ok", row, []


def save_questionnaire_response(
    db: Session, questionnaire_id: int, payload: QuestionnaireResponseSave
) -> tuple[Outcome, QuestionnaireResponse | None, list[str]]:
    q = get_questionnaire(db, questionnaire_id)
    if q is None:
        return "questionnaire_not_found", None, []

    if q.status == QuestionnaireStatus.approved:
        return "forbidden_approved", None, []
    if q.status == QuestionnaireStatus.submitted:
        return "forbidden_submitted", None, []

    merged_dict = payload.response_data.model_dump(mode="python")
    ok, errors = validate_response_structure(merged_dict)
    if not ok:
        return "validation_error", None, errors

    existing = _get_response_row(db, questionnaire_id)
    revision_fb = _extract_revision_feedback(
        existing.response_data if existing else None
    )

    stored = payload.response_data.to_stored_dict(revision_fb)
    val_ok, val_errs = validate_response_structure(stored)
    if not val_ok:
        return "validation_error", None, val_errs

    validation_errors: list[str] | None = None
    vstatus = ValidationStatus.valid
    if existing is None:
        row = QuestionnaireResponse(
            questionnaire_id=questionnaire_id,
            response_data=stored,
            validation_status=vstatus,
            validation_errors=validation_errors,
        )
        db.add(row)
    else:
        row = existing
        row.response_data = stored
        row.validation_status = vstatus
        row.validation_errors = validation_errors

    db.commit()
    db.refresh(row)
    return "ok", row, []


def submit_questionnaire(
    db: Session, questionnaire_id: int
) -> tuple[Outcome, Questionnaire | None, list[str]]:
    q = get_questionnaire(db, questionnaire_id)
    if q is None:
        return "questionnaire_not_found", None, []

    if q.status == QuestionnaireStatus.submitted:
        return "invalid_transition", q, [
            "Questionnaire is already submitted; wait for review or revision"
        ]
    if q.status == QuestionnaireStatus.approved:
        return "invalid_transition", q, ["Questionnaire is already approved"]
    if q.status not in (
        QuestionnaireStatus.draft,
        QuestionnaireStatus.needs_revision,
    ):
        return "invalid_transition", q, [f"Cannot submit from status {q.status.value}"]

    row = _get_response_row(db, questionnaire_id)
    if row is None:
        return "validation_error", None, ["No response data to submit"]

    raw = row.response_data
    ok, errs = validate_submit_ready(raw)
    if not ok:
        return "validation_error", None, errs

    if isinstance(raw, dict):
        cleaned = {k: v for k, v in raw.items() if k != "revision_feedback"}
        row.response_data = cleaned

    q.status = QuestionnaireStatus.submitted
    q.submitted_at = _utcnow()
    row.validation_status = ValidationStatus.valid
    row.validation_errors = None

    db.commit()
    db.refresh(q)
    db.refresh(row)
    return "ok", q, []


def return_questionnaire_for_revision(
    db: Session, questionnaire_id: int, reason: str
) -> tuple[Outcome, Questionnaire | None, list[str]]:
    q = get_questionnaire(db, questionnaire_id)
    if q is None:
        return "questionnaire_not_found", None, []

    if q.status != QuestionnaireStatus.submitted:
        return "invalid_transition", q, [
            "Return for revision is only allowed from submitted status"
        ]

    row = _get_response_row(db, questionnaire_id)
    if row is None:
        return "response_not_found", None, []

    data = dict(row.response_data) if isinstance(row.response_data, dict) else {}
    data["revision_feedback"] = reason.strip()
    row.response_data = data
    q.status = QuestionnaireStatus.needs_revision

    db.commit()
    db.refresh(q)
    db.refresh(row)
    return "ok", q, []


def approve_questionnaire(
    db: Session, questionnaire_id: int
) -> tuple[Outcome, Questionnaire | None, list[str]]:
    q = get_questionnaire(db, questionnaire_id)
    if q is None:
        return "questionnaire_not_found", None, []

    if q.status != QuestionnaireStatus.submitted:
        return "invalid_transition", q, ["Approve is only allowed from submitted status"]

    q.status = QuestionnaireStatus.approved
    db.commit()
    db.refresh(q)
    return "ok", q, []


def reopen_questionnaire_draft(
    db: Session, questionnaire_id: int
) -> tuple[Outcome, Questionnaire | None, list[str]]:
    q = get_questionnaire(db, questionnaire_id)
    if q is None:
        return "questionnaire_not_found", None, []

    if q.status != QuestionnaireStatus.needs_revision:
        return "invalid_transition", q, [
            "Reopen as draft is only allowed from needs_revision status"
        ]

    q.status = QuestionnaireStatus.draft
    q.submitted_at = None
    db.commit()
    db.refresh(q)
    return "ok", q, []


def status_change_message(status: QuestionnaireStatus) -> str:
    return f"Questionnaire status is now {status.value}"
