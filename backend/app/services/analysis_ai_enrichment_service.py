"""
AI enrichment для отчёта анализа (POST /analyze): объяснения, резюме, NLP (нормализация, NER, RE).

Не изменяет rule-based поля AnalysisReport — только опциональный блок ai_enrichment.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import Settings
from app.schemas.analysis_report import (
    AiAnalysisEnrichment,
    AnalysisReport,
    ClassifiedAssetItem,
    NlpEntityItem,
    NlpRelationItem,
)
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

_RE_INDEXED = re.compile(r"^([a-z_]+)\[(\d+)\]$")


def _serialize_mixed_list(val: Any, *, max_items: int = 30) -> str:
    if not isinstance(val, list) or not val:
        return ""
    parts: list[str] = []
    for item in val[:max_items]:
        if isinstance(item, dict):
            parts.append(json.dumps(item, ensure_ascii=False, default=str))
        else:
            parts.append(str(item))
    return "\n".join(parts)


def collect_nlp_text_fragments(response_data: dict[str, Any]) -> list[dict[str, str]]:
    """
    Текстовые фрагменты анкеты для NLP (по факту хранимой структуры response_data / фронта).

    Подключено:
    - additional_notes
    - department_profile: description, manager_name, contact_info
    - incidents[]: summary + details
    - contractors[]: name + details
    - access_matrix[]: resource + note
    - business_processes[]: name + used_asset_ids
    - assets[]: id, name, asset_type, owner (структурированные поля как одна строка для контекста NER)
    """
    out: list[dict[str, str]] = []

    notes = response_data.get("additional_notes")
    if isinstance(notes, str) and notes.strip():
        out.append({"source_field": "additional_notes", "text": notes.strip()})

    dp = response_data.get("department_profile")
    if isinstance(dp, dict):
        for key in ("description", "manager_name", "contact_info"):
            v = dp.get(key)
            if isinstance(v, str) and v.strip():
                out.append(
                    {
                        "source_field": f"department_profile.{key}",
                        "text": v.strip(),
                    }
                )

    incidents = response_data.get("incidents")
    if isinstance(incidents, list):
        for i, row in enumerate(incidents):
            if not isinstance(row, dict):
                continue
            s = str(row.get("summary") or row.get("name") or "").strip()
            d = str(row.get("details") or row.get("note") or "").strip()
            line = f"{s}\n{d}".strip() if d else s
            if line:
                out.append({"source_field": f"incidents[{i}]", "text": line})

    contractors = response_data.get("contractors")
    if isinstance(contractors, list):
        for i, row in enumerate(contractors):
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            det = str(row.get("details") or "").strip()
            line = f"{name}\n{det}".strip() if det else name
            if line:
                out.append({"source_field": f"contractors[{i}]", "text": line})

    matrix = response_data.get("access_matrix")
    if isinstance(matrix, list):
        for i, row in enumerate(matrix):
            if not isinstance(row, dict):
                continue
            res = str(row.get("resource") or "").strip()
            note = str(row.get("note") or "").strip()
            line = f"{res}\n{note}".strip() if note else res
            if line:
                out.append({"source_field": f"access_matrix[{i}]", "text": line})

    processes = response_data.get("business_processes")
    if isinstance(processes, list):
        for i, row in enumerate(processes):
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            used = row.get("used_asset_ids")
            if isinstance(used, list):
                used_s = ", ".join(str(x).strip() for x in used if str(x).strip())
            else:
                used_s = str(used or "").strip()
            line = f"{name}\nСвязанные активы: {used_s}".strip() if used_s else name
            if line:
                out.append({"source_field": f"business_processes[{i}]", "text": line})

    assets = response_data.get("assets")
    if isinstance(assets, list):
        for i, row in enumerate(assets):
            if not isinstance(row, dict):
                continue
            aid = str(row.get("id") or "").strip()
            name = str(row.get("name") or "").strip()
            at = str(row.get("asset_type") or "").strip()
            owner = str(row.get("owner") or row.get("owner_name") or "").strip()
            nz = str(row.get("network_zone") or "").strip()
            proto = str(row.get("protocols") or "").strip()
            ven = str(row.get("vendor") or "").strip()
            parts = [p for p in (aid, name, at, owner, nz, proto, ven) if p]
            for tag, key in (
                ("mfa", "supports_mfa"),
                ("patch", "supports_patching"),
                ("safety_critical", "safety_critical"),
            ):
                v = row.get(key)
                if v is not None and str(v).strip() != "":
                    parts.append(f"{tag}={v}")
            if parts:
                line = " | ".join(parts)
                out.append({"source_field": f"assets[{i}]", "text": line})

    return out


def _build_labeled_nlp_document(fragments: list[dict[str, str]]) -> str:
    blocks: list[str] = []
    for fr in fragments:
        sf = fr.get("source_field") or ""
        tx = (fr.get("text") or "").strip()
        if not tx:
            continue
        blocks.append(f"<<<SOURCE:{sf}>>>\n{tx}")
    return "\n\n".join(blocks).strip()


def _normalized_rows_to_bundle(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Преобразует плоский список нормализованных фрагментов в вложенный normalized_text для API."""
    bundle: dict[str, Any] = {}
    dp: dict[str, str] = {}
    indexed_lists: dict[str, dict[int, str]] = {}

    for row in rows:
        sf = (row.get("source_field") or "").strip()
        norm = (row.get("normalized") or "").strip()
        if not sf:
            continue
        if sf == "additional_notes":
            if norm:
                bundle["additional_notes"] = norm
            continue
        if sf.startswith("department_profile."):
            sub = sf.split(".", 1)[-1]
            if sub and norm:
                dp[sub] = norm
            continue
        m = _RE_INDEXED.match(sf)
        if m and norm:
            section = m.group(1)
            idx = int(m.group(2))
            indexed_lists.setdefault(section, {})[idx] = norm
            continue
        if norm:
            bundle.setdefault("other", []).append({"source_field": sf, "normalized": norm})

    if dp:
        bundle["department_profile"] = dp

    for section, idx_map in indexed_lists.items():
        ordered = [idx_map[k] for k in sorted(idx_map.keys())]
        compact = [x for x in ordered if (x or "").strip()]
        if compact:
            bundle[section] = compact

    return bundle


async def _run_questionnaire_nlp_pipeline(
    ai: AIService,
    response_data: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[NlpEntityItem] | None, list[NlpRelationItem] | None, bool]:
    """
    Нормализация + NER + RE по текстам анкеты.
    Возвращает (normalized_text | None, entities | None, relations | None, normalization_ok).
    """
    fragments = collect_nlp_text_fragments(response_data)
    n_frag = len(fragments)
    logger.info("analysis nlp: collected text fragments=%s", n_frag)
    if not fragments:
        return None, None, None, True

    norm_rows, norm_ok = await ai.normalize_questionnaire_fragments(fragments)
    logger.info(
        "analysis nlp: normalization success=%s normalized_rows=%s",
        norm_ok,
        len(norm_rows),
    )
    normalized_bundle: dict[str, Any] | None = None
    if norm_ok and norm_rows:
        merged = _normalized_rows_to_bundle(norm_rows)
        if merged:
            normalized_bundle = merged

    labeled = _build_labeled_nlp_document(fragments)
    entities_raw = await ai.extract_questionnaire_entities(labeled)
    relations_raw = await ai.extract_relations_from_text(labeled)

    entities: list[NlpEntityItem] | None = None
    if entities_raw:
        entities = []
        for e in entities_raw:
            try:
                entities.append(NlpEntityItem.model_validate(e))
            except Exception:  # noqa: BLE001
                continue
        if not entities:
            entities = None

    relations: list[NlpRelationItem] | None = None
    if relations_raw:
        relations = []
        for r in relations_raw:
            try:
                relations.append(NlpRelationItem.model_validate(r))
            except Exception:  # noqa: BLE001
                continue
        if not relations:
            relations = None

    logger.info(
        "analysis nlp: entities=%s relations=%s",
        len(entities or []),
        len(relations or []),
    )
    return normalized_bundle, entities, relations, norm_ok


def collect_questionnaire_notes_text(response_data: dict[str, Any]) -> str:
    """Собирает только текстовые/списочные секции для резюме; не трогает core-анализ."""
    blocks: list[str] = []

    notes = response_data.get("additional_notes")
    if isinstance(notes, str) and notes.strip():
        blocks.append(f"[additional_notes]\n{notes.strip()}")

    for key, label in (
        ("incidents", "incidents"),
        ("contractors", "contractors"),
        ("access_matrix", "access_matrix"),
    ):
        raw = response_data.get(key)
        if raw is None:
            continue
        serialized = _serialize_mixed_list(raw)
        if serialized:
            blocks.append(f"[{label}]\n{serialized}")

    dp = response_data.get("department_profile")
    if isinstance(dp, dict):
        desc = dp.get("description")
        if isinstance(desc, str) and desc.strip():
            blocks.append(f"[department_profile.description]\n{desc.strip()}")

    return "\n\n".join(blocks).strip()


async def enrich_analysis_report_with_ai(
    report: AnalysisReport,
    response_data: dict[str, Any],
    ai: AIService,
    settings: Settings,
) -> AnalysisReport:
    """
    Добавляет ai_enrichment к уже посчитанному rule-based отчёту.
    При любых сбоях LLM возвращает исходный report без ai_enrichment.
    """
    if not settings.analysis_use_llm:
        return report

    if not (settings.openrouter_api_key or "").strip():
        logger.info("analysis ai_enrichment skipped: OPENROUTER_API_KEY missing")
        return report

    n_risks = len(report.risks)
    n_links = len(report.links)
    logger.info(
        "analysis ai_enrichment started: risks=%s links=%s model=%s",
        n_risks,
        n_links,
        settings.openrouter_model,
    )

    classified_by_asset: dict[str, ClassifiedAssetItem] = {
        c.asset_id: c for c in report.classified_assets
    }

    risk_expl: dict[str, str] = {}
    for risk in report.risks:
        key = f"asset:{risk.asset_id}|risk:{risk.risk_code}"
        ca = classified_by_asset.get(risk.asset_id)
        asset_ctx: dict[str, Any] = {
            "asset_id": risk.asset_id,
            "environment": ca.environment if ca else None,
            "original_criticality": ca.original_criticality if ca else None,
            "effective_criticality": ca.effective_criticality if ca else None,
            "usage_count": ca.usage_count if ca else None,
            "rule_engine_notes": list(ca.notes) if ca else [],
        }
        risk_ctx: dict[str, Any] = {
            "risk_code": risk.risk_code,
            "title": risk.title,
            "severity": risk.severity,
        }
        try:
            risk_expl[key] = await ai.explain_risk_for_analysis(asset_ctx, risk_ctx)
        except (RuntimeError, httpx.TimeoutException, httpx.HTTPError, OSError) as e:
            logger.error("analysis ai_enrichment risk %s failed: %s", key, e)

    link_expl: dict[str, str] = {}
    for idx, link in enumerate(report.links):
        key = f"link:{idx}"
        ctx = {
            "asset_id": link.asset_id,
            "risk": link.risk,
            "requirement": link.requirement,
            "measure": link.measure,
        }
        try:
            link_expl[key] = await ai.explain_analysis_link(ctx)
        except (RuntimeError, httpx.TimeoutException, httpx.HTTPError, OSError) as e:
            logger.error("analysis ai_enrichment %s failed: %s", key, e)

    notes_summary: str | None = None
    combined = collect_questionnaire_notes_text(response_data)
    if combined:
        try:
            summary = await ai.summarize_questionnaire_notes(combined)
            if summary.strip():
                notes_summary = summary.strip()
        except (RuntimeError, httpx.TimeoutException, httpx.HTTPError, OSError) as e:
            logger.error("analysis ai_enrichment notes_summary failed: %s", e)

    norm_text, nlp_entities, nlp_relations, norm_ok = await _run_questionnaire_nlp_pipeline(
        ai,
        response_data,
    )

    nlp_has = bool(
        norm_text
        or (nlp_entities and len(nlp_entities) > 0)
        or (nlp_relations and len(nlp_relations) > 0)
    )
    has_output = bool(
        risk_expl
        or link_expl
        or (notes_summary and notes_summary.strip())
        or nlp_has
    )
    if not has_output:
        logger.warning(
            "analysis ai_enrichment finished with no LLM output; ai_enrichment omitted",
        )
        return report

    enrichment = AiAnalysisEnrichment(
        risk_explanations=risk_expl,
        link_explanations=link_expl,
        notes_summary=notes_summary,
        normalized_text=norm_text,
        entities=nlp_entities,
        relations=nlp_relations,
        llm_used=True,
        model=settings.openrouter_model,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    logger.info(
        "analysis ai_enrichment completed: risk_explanations=%s link_explanations=%s "
        "has_notes_summary=%s normalized_text=%s entities=%s relations=%s nlp_norm_ok=%s",
        len(risk_expl),
        len(link_expl),
        bool(notes_summary),
        bool(norm_text),
        len(nlp_entities or []),
        len(nlp_relations or []),
        norm_ok,
    )
    return report.model_copy(update={"ai_enrichment": enrichment})
