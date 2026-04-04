"""CRUD для PolicyDocument и PolicyVersion (доменные сущности БД)."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.policy_document import PolicyDocument
from app.models.policy_version import PolicyVersion
from app.schemas.policy import (
    PolicyDocumentCreate,
    PolicyDocumentUpdate,
    PolicyVersionCreate,
)

logger = logging.getLogger(__name__)


def compute_source_hash(response_data: dict[str, Any], analysis_result: dict[str, Any]) -> str:
    """SHA-256 от канонического JSON источников (анкета + анализ)."""
    payload = json.dumps(
        {"response_data": response_data, "analysis_result": analysis_result},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_snapshot_list(snapshot: dict[str, Any], key: str) -> list[str]:
    raw = snapshot.get(key)
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(
                json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
            )
        else:
            s = str(item).strip()
            if s:
                out.append(s)
    return out


def compute_diff(old_snapshot: dict[str, Any], new_snapshot: dict[str, Any]) -> dict[str, Any]:
    """
    Сравнение снимков политики по разделам assets, risks, measures.

    Возвращает dict с ключами assets/risks/measures и для каждого:
    added, removed, changed (для списков строк — changed обычно пуст).
    """
    result: dict[str, Any] = {}
    for key in ("assets", "risks", "measures"):
        old_set = set(_normalize_snapshot_list(old_snapshot, key))
        new_set = set(_normalize_snapshot_list(new_snapshot, key))
        result[key] = {
            "added": sorted(new_set - old_set),
            "removed": sorted(old_set - new_set),
            "changed": [],
        }
    return result


def get_latest_policy_version(
    db: Session, policy_document_id: int
) -> PolicyVersion | None:
    return db.scalar(
        select(PolicyVersion)
        .where(PolicyVersion.policy_document_id == policy_document_id)
        .order_by(PolicyVersion.version_number.desc())
        .limit(1)
    )


def get_policy_version_by_number(
    db: Session, policy_document_id: int, version_number: int
) -> PolicyVersion | None:
    return db.scalar(
        select(PolicyVersion).where(
            PolicyVersion.policy_document_id == policy_document_id,
            PolicyVersion.version_number == version_number,
        )
    )


def create_new_version_if_needed(
    db: Session,
    *,
    questionnaire_id: int,
    policy_document_id: int,
    policy_data: dict[str, Any],
    response_data: dict[str, Any],
    analysis_result: dict[str, Any],
) -> tuple[Literal["skipped", "unchanged", "created"], PolicyVersion | None, str]:
    """
    Если хеш источников совпадает с последней версией — новая запись не создаётся.

    Returns:
        (status, version_or_none, source_hash_hex)
    """
    doc = get_policy_document(db, policy_document_id)
    if doc is None:
        logger.warning(
            "create_new_version_if_needed: policy_document_id=%s not found (q=%s)",
            policy_document_id,
            questionnaire_id,
        )
        return "skipped", None, ""

    rd = response_data if isinstance(response_data, dict) else {}
    ar = analysis_result if isinstance(analysis_result, dict) else {}
    new_hash = compute_source_hash(rd, ar)

    latest = get_latest_policy_version(db, policy_document_id)
    if latest is not None and (latest.source_hash or "") == new_hash:
        logger.info(
            "Policy version unchanged policy_id=%s hash=%s… q=%s",
            policy_document_id,
            new_hash[:12],
            questionnaire_id,
        )
        return "unchanged", None, new_hash

    next_num = (latest.version_number + 1) if latest else 1
    md_body = policy_data.get("general") if isinstance(policy_data.get("general"), str) else ""
    content_markdown = (md_body.strip() or "# Политика информационной безопасности")[:8000]

    ver = PolicyVersion(
        policy_document_id=policy_document_id,
        version_number=next_num,
        content_markdown=content_markdown,
        content_html=None,
        source_hash=new_hash,
        snapshot=dict(policy_data) if isinstance(policy_data, dict) else {},
        generated_from_analysis=ar or None,
        change_summary=(
            f"Автоверсия {next_num} (анкета id={questionnaire_id}, hash={new_hash[:16]}…)"
        )[:1024],
    )
    db.add(ver)
    db.flush()

    doc.current_version_id = ver.id
    db.commit()
    db.refresh(ver)
    db.refresh(doc)

    logger.info(
        "Policy version created policy_id=%s version=%s q=%s",
        policy_document_id,
        next_num,
        questionnaire_id,
    )
    return "created", ver, new_hash


def list_policy_documents(db: Session, *, skip: int, limit: int) -> list[PolicyDocument]:
    stmt = select(PolicyDocument).order_by(PolicyDocument.id).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def get_policy_document(db: Session, policy_id: int) -> PolicyDocument | None:
    return db.get(PolicyDocument, policy_id)


def create_policy_document(db: Session, data: PolicyDocumentCreate) -> PolicyDocument:
    obj = PolicyDocument(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_policy_document(
    db: Session, policy_id: int, data: PolicyDocumentUpdate
) -> PolicyDocument | str | None:
    """
    Returns updated PolicyDocument, None if not found, or error string if
    current_version_id is invalid for this document.
    """
    obj = get_policy_document(db, policy_id)
    if obj is None:
        return None
    payload = data.model_dump(exclude_unset=True)
    if "current_version_id" in payload:
        vid = payload["current_version_id"]
        if vid is not None:
            ver = db.get(PolicyVersion, vid)
            if ver is None or ver.policy_document_id != policy_id:
                return "invalid_current_version"
    for key, value in payload.items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_policy_document(db: Session, policy_id: int) -> bool:
    obj = get_policy_document(db, policy_id)
    if obj is None:
        return False
    db.delete(obj)
    db.commit()
    return True


def list_policy_versions(
    db: Session,
    *,
    skip: int,
    limit: int,
    policy_document_id: int | None = None,
) -> list[PolicyVersion]:
    stmt = select(PolicyVersion).order_by(
        PolicyVersion.policy_document_id,
        PolicyVersion.version_number,
    )
    if policy_document_id is not None:
        stmt = stmt.where(PolicyVersion.policy_document_id == policy_document_id)
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def get_policy_version(db: Session, version_id: int) -> PolicyVersion | None:
    return db.get(PolicyVersion, version_id)


def create_policy_version(
    db: Session, data: PolicyVersionCreate
) -> PolicyVersion | str | None:
    """
    Returns PolicyVersion, None if policy document missing,
    or 'duplicate_version' if version_number exists for document.
    """
    if get_policy_document(db, data.policy_document_id) is None:
        return None
    existing = db.scalar(
        select(PolicyVersion).where(
            PolicyVersion.policy_document_id == data.policy_document_id,
            PolicyVersion.version_number == data.version_number,
        )
    )
    if existing is not None:
        return "duplicate_version"
    obj = PolicyVersion(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
