"""
Логическая валидация данных анкеты (response_data) перед этапом анализа.

Соглашения по JSON (MVP):
- assets[]: объекты с полем id (str | int), owner или owner_name (непустая строка),
  criticality ∈ {low, medium, high, critical}.
- business_processes[]: объекты с name (непустая строка) и used_asset_ids или asset_ids
  (массив идентификаторов активов, как в assets[].id).
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.validation import ValidationIssue, ValidationResult
from app.services import questionnaire_collection_service as qc

ALLOWED_CRITICALITY = frozenset({"low", "medium", "high", "critical"})

# Простая эвристика «подозрительно низкая критичность» для OT/критичных маркеров
_CRITICALITY_HINT_PATTERN = re.compile(
    r"\b(scada|plc|dcs|mes|erp|ot|кск|плк|срп|асу)\b",
    re.IGNORECASE,
)


def is_ready_for_analysis(result: ValidationResult) -> bool:
    """Использовать перед запуском анализа: при False данные в анализ не передавать."""
    return result.is_valid


def validate_questionnaire(
    db: Session, questionnaire_id: int
) -> tuple[str | None, ValidationResult | None]:
    """
    Загружает актуальный ответ анкеты и выполняет validate_response_data.

    Returns:
        (None, result) при успехе;
        ("questionnaire_not_found", None) или ("response_not_found", None).
    """
    outcome, row, _ = qc.get_questionnaire_response(db, questionnaire_id)
    if outcome == "questionnaire_not_found":
        return "questionnaire_not_found", None
    if outcome == "response_not_found":
        return "response_not_found", None
    assert row is not None
    raw = row.response_data
    data = dict(raw) if isinstance(raw, dict) else {}
    return None, validate_response_data(data)


def validate_response_data(response_data: dict[str, Any]) -> ValidationResult:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    ok, struct_msgs = qc.validate_response_structure(response_data)
    if not ok:
        for msg in struct_msgs:
            errors.append(
                ValidationIssue(
                    code="STRUCTURE_ERROR",
                    field="response_data",
                    message=msg,
                )
            )
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    _validate_required_sections(response_data, errors)

    assets = response_data.get("assets", [])
    if not isinstance(assets, list):
        assets = []

    asset_errors, asset_warnings, asset_ids, id_to_asset = validate_assets(assets)
    errors.extend(asset_errors)
    warnings.extend(asset_warnings)

    processes = response_data.get("business_processes", [])
    if not isinstance(processes, list):
        processes = []

    proc_errors, proc_warnings = validate_business_processes(processes)
    errors.extend(proc_errors)
    warnings.extend(proc_warnings)

    if not errors:
        validate_cross_links(processes, asset_ids, errors)

    if not errors:
        validate_contradictions(assets, processes, asset_ids, id_to_asset, warnings)

    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


def _validate_required_sections(data: dict[str, Any], errors: list[ValidationIssue]) -> None:
    dp = data.get("department_profile")
    if not isinstance(dp, dict) or not _profile_non_empty(dp):
        errors.append(
            ValidationIssue(
                code="EMPTY_DEPARTMENT_PROFILE",
                field="department_profile",
                message="department_profile must contain at least one non-empty field "
                "(description, manager_name, contact_info)",
            )
        )

    assets = data.get("assets")
    if not isinstance(assets, list) or len(assets) < 1:
        errors.append(
            ValidationIssue(
                code="EMPTY_ASSETS",
                field="assets",
                message="Assets list cannot be empty",
            )
        )

    bps = data.get("business_processes")
    if not isinstance(bps, list) or len(bps) < 1:
        errors.append(
            ValidationIssue(
                code="EMPTY_BUSINESS_PROCESSES",
                field="business_processes",
                message="business_processes list cannot be empty",
            )
        )


def _profile_non_empty(profile: dict[str, Any]) -> bool:
    for k in ("description", "manager_name", "contact_info"):
        v = profile.get(k)
        if isinstance(v, str) and v.strip():
            return True
    return False


def validate_assets(
    assets: list[Any],
) -> tuple[list[ValidationIssue], list[ValidationIssue], set[str], dict[str, dict[str, Any]]]:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    seen: set[str] = set()
    id_to_asset: dict[str, dict[str, Any]] = {}

    for idx, item in enumerate(assets):
        field_prefix = f"assets[{idx}]"
        if not isinstance(item, dict):
            errors.append(
                ValidationIssue(
                    code="ASSET_NOT_OBJECT",
                    field=field_prefix,
                    message="Each asset must be a JSON object",
                )
            )
            continue

        aid = item.get("id")
        if aid is None or (isinstance(aid, str) and not aid.strip()):
            errors.append(
                ValidationIssue(
                    code="MISSING_ASSET_ID",
                    field=f"{field_prefix}.id",
                    message="Each asset must have a non-empty id for cross-references",
                )
            )
            continue

        sid = str(aid).strip()
        if sid in seen:
            errors.append(
                ValidationIssue(
                    code="DUPLICATE_ASSET_ID",
                    field=f"{field_prefix}.id",
                    message=f"Duplicate asset id: {sid}",
                )
            )
            continue
        seen.add(sid)
        id_to_asset[sid] = item

        owner = item.get("owner") if item.get("owner") is not None else item.get("owner_name")
        if owner is None or not isinstance(owner, str) or not owner.strip():
            errors.append(
                ValidationIssue(
                    code="MISSING_OWNER",
                    field=f"{field_prefix}.owner",
                    message="Asset must have non-empty owner or owner_name",
                )
            )

        crit = item.get("criticality")
        if crit is None or not isinstance(crit, str) or not crit.strip():
            errors.append(
                ValidationIssue(
                    code="MISSING_CRITICALITY",
                    field=f"{field_prefix}.criticality",
                    message="Asset must have criticality (low, medium, high, critical)",
                )
            )
        elif crit.strip().lower() not in ALLOWED_CRITICALITY:
            errors.append(
                ValidationIssue(
                    code="INVALID_CRITICALITY",
                    field=f"{field_prefix}.criticality",
                    message=f"criticality must be one of: {sorted(ALLOWED_CRITICALITY)}",
                )
            )
        else:
            _maybe_warn_low_criticality(item, sid, field_prefix, warnings)

    return errors, warnings, seen, id_to_asset


def _maybe_warn_low_criticality(
    asset: dict[str, Any],
    sid: str,
    field_prefix: str,
    warnings: list[ValidationIssue],
) -> None:
    crit = str(asset.get("criticality", "")).strip().lower()
    if crit != "low":
        return
    name = str(asset.get("name", "") or "")
    atype = str(asset.get("asset_type", "") or "")
    blob = f"{name} {atype}"
    if _CRITICALITY_HINT_PATTERN.search(blob):
        warnings.append(
            ValidationIssue(
                code="LOW_CRITICALITY_SUSPICIOUS",
                field=f"asset_{sid}",
                message="Asset name/type suggests OT/critical system but criticality is low",
            )
        )


def validate_business_processes(
    processes: list[Any],
) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    for idx, item in enumerate(processes):
        prefix = f"business_processes[{idx}]"
        if not isinstance(item, dict):
            errors.append(
                ValidationIssue(
                    code="PROCESS_NOT_OBJECT",
                    field=prefix,
                    message="Each business process must be a JSON object",
                )
            )
            continue

        name = item.get("name")
        if name is None or not isinstance(name, str) or not name.strip():
            errors.append(
                ValidationIssue(
                    code="MISSING_PROCESS_NAME",
                    field=f"{prefix}.name",
                    message="Business process must have a non-empty name",
                )
            )

        used = item.get("used_asset_ids")
        if used is None:
            used = item.get("asset_ids")
        if used is None:
            errors.append(
                ValidationIssue(
                    code="MISSING_USED_ASSET_IDS",
                    field=f"{prefix}.used_asset_ids",
                    message="Business process must include used_asset_ids (or asset_ids) array",
                )
            )
        elif not isinstance(used, list):
            errors.append(
                ValidationIssue(
                    code="USED_ASSET_IDS_NOT_LIST",
                    field=f"{prefix}.used_asset_ids",
                    message="used_asset_ids must be an array",
                )
            )

    return errors, warnings


def validate_cross_links(
    processes: list[Any],
    asset_ids: set[str],
    errors: list[ValidationIssue],
) -> None:
    for idx, item in enumerate(processes):
        if not isinstance(item, dict):
            continue
        prefix = f"business_processes[{idx}]"
        used = item.get("used_asset_ids")
        if used is None:
            used = item.get("asset_ids")
        if not isinstance(used, list):
            continue
        proc_name = item.get("name", str(idx))
        label = proc_name if isinstance(proc_name, str) else str(idx)
        for ref_idx, ref in enumerate(used):
            if ref is None:
                errors.append(
                    ValidationIssue(
                        code="NULL_ASSET_REFERENCE",
                        field=f"{prefix}.used_asset_ids[{ref_idx}]",
                        message=f"Process «{label}» contains null asset reference",
                    )
                )
                continue
            sid = str(ref).strip()
            if sid not in asset_ids:
                errors.append(
                    ValidationIssue(
                        code="UNKNOWN_ASSET_REFERENCE",
                        field=f"{prefix}.used_asset_ids[{ref_idx}]",
                        message=f'Process «{label}» references unknown asset_id "{sid}"',
                    )
                )


def validate_contradictions(
    assets: list[Any],
    processes: list[Any],
    asset_ids: set[str],
    id_to_asset: dict[str, dict[str, Any]],
    warnings: list[ValidationIssue],
) -> None:
    used: set[str] = set()
    for item in processes:
        if not isinstance(item, dict):
            continue
        raw = item.get("used_asset_ids")
        if raw is None:
            raw = item.get("asset_ids")
        if not isinstance(raw, list):
            continue
        if len(raw) == 0:
            name = item.get("name", "?")
            label = name if isinstance(name, str) else "?"
            warnings.append(
                ValidationIssue(
                    code="PROCESS_WITHOUT_ASSETS",
                    field="business_processes",
                    message=f'Process «{label}» has empty list of used assets',
                )
            )
            continue
        for ref in raw:
            if ref is not None:
                used.add(str(ref).strip())

    highish = {"high", "critical"}
    for sid in asset_ids:
        a = id_to_asset.get(sid)
        if not a:
            continue
        crit = str(a.get("criticality", "")).strip().lower()
        if crit in highish and sid not in used:
            warnings.append(
                ValidationIssue(
                    code="HIGH_CRITICALITY_UNUSED",
                    field=f"asset_{sid}",
                    message=f'High/critical asset "{sid}" is not referenced by any business process',
                )
            )
