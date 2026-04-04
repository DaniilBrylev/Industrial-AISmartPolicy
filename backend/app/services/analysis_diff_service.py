"""
Сравнение двух отчётов анализа (MVP актуализации): риски, меры, traceability, разделы политики.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.schemas.analysis_report import AnalysisReport, RiskItem, TraceabilityEntry

logger = logging.getLogger(__name__)


def _risk_identity(r: RiskItem) -> str:
    return f"{r.asset_id}|{r.risk_code}"


def _trace_identity(e: TraceabilityEntry) -> str:
    return (
        f"{e.asset_id}|{e.risk_code}|{e.requirement_key}|"
        f"{(e.measure_title or '').strip()}"
    )


def _canonical_assets(assets: list[dict[str, Any]]) -> str:
    return json.dumps(assets, sort_keys=True, ensure_ascii=False, default=str)


def _classified_signature(report: AnalysisReport) -> str:
    return json.dumps(
        [c.model_dump(mode="json") for c in report.classified_assets],
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )


def _traceability_entries(report: AnalysisReport) -> list[TraceabilityEntry]:
    if report.traceability_map is None:
        return []
    return list(report.traceability_map.entries)


def build_analysis_diff(
    old: AnalysisReport | None,
    new: AnalysisReport,
) -> dict[str, Any]:
    """
    Собирает структуру analysis_diff для API. old — сохранённый отчёт; new — свежий rule-based (+ traceability).
    """
    logger.info("analysis diff build started")
    old = old or AnalysisReport()

    old_risks = {_risk_identity(r): r for r in old.risks}
    new_risks = {_risk_identity(r): r for r in new.risks}
    added_risk_keys = set(new_risks) - set(old_risks)
    removed_risk_keys = set(old_risks) - set(new_risks)
    added_risks = [new_risks[k].model_dump(mode="json") for k in sorted(added_risk_keys)]
    removed_risks = [old_risks[k].model_dump(mode="json") for k in sorted(removed_risk_keys)]

    old_meas = set(old.measures)
    new_meas = set(new.measures)
    added_measures = sorted(new_meas - old_meas)
    removed_measures = sorted(old_meas - new_meas)

    old_tr = {_trace_identity(e): e for e in _traceability_entries(old)}
    new_tr = {_trace_identity(e): e for e in _traceability_entries(new)}
    add_tr_keys = set(new_tr) - set(old_tr)
    rem_tr_keys = set(old_tr) - set(new_tr)
    added_traceability_entries = [
        new_tr[k].model_dump(mode="json") for k in sorted(add_tr_keys)
    ]
    removed_traceability_entries = [
        old_tr[k].model_dump(mode="json") for k in sorted(rem_tr_keys)
    ]

    assets_changed = _canonical_assets(old.assets) != _canonical_assets(new.assets)
    classified_changed = _classified_signature(old) != _classified_signature(new)
    req_changed = list(old.requirements) != list(new.requirements)
    risks_changed = bool(added_risk_keys or removed_risk_keys)
    meas_changed = bool(added_measures or removed_measures)
    tr_changed = bool(add_tr_keys or rem_tr_keys)

    policy_sections: list[str] = []
    if assets_changed:
        policy_sections.append("Активы")
    if classified_changed or assets_changed:
        if "Классификация и среда" not in policy_sections:
            policy_sections.append("Классификация и среда")
    if risks_changed:
        policy_sections.append("Риски")
    if req_changed or tr_changed:
        if "Требования" not in policy_sections:
            policy_sections.append("Требования")
    if meas_changed or tr_changed:
        if "Меры защиты" not in policy_sections:
            policy_sections.append("Меры защиты")

    has_changes = any(
        [
            assets_changed,
            classified_changed,
            risks_changed,
            meas_changed,
            req_changed,
            tr_changed,
        ]
    )

    summary: list[str] = []
    for r in added_risks:
        summary.append(f"Добавлен риск: {r.get('risk_code', '')} ({r.get('title', '')})")
    for r in removed_risks:
        summary.append(f"Удалён риск: {r.get('risk_code', '')} ({r.get('title', '')})")
    for m in added_measures:
        summary.append(f"Добавлена мера: {m}")
    for m in removed_measures:
        summary.append(f"Удалена мера: {m}")
    if policy_sections:
        summary.append(
            "Изменятся разделы политики: " + ", ".join(policy_sections),
        )

    out = {
        "has_changes": has_changes,
        "summary": summary,
        "added_risks": added_risks,
        "removed_risks": removed_risks,
        "added_measures": added_measures,
        "removed_measures": removed_measures,
        "added_traceability_entries": added_traceability_entries,
        "removed_traceability_entries": removed_traceability_entries,
        "policy_sections_changed": policy_sections,
    }
    logger.info(
        "analysis diff completed: has_changes=%s policy sections changed = %s",
        has_changes,
        policy_sections,
    )
    return out
