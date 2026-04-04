"""
Сборка explainability / XAI payload из уже посчитанного analysis_result и response_data (без новых решений).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from app.schemas.analysis_report import (
    AnalysisReport,
    ClassifiedAssetItem,
    ExplanationAssetRef,
    ExplanationPayload,
    RiskItem,
    TraceabilityEntry,
)
from app.services import analysis_service as asvc
from app.services import analysis_ot_support as ot_sup

logger = logging.getLogger(__name__)

Kind = Literal["risk", "traceability"]


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _asset_row(assets: list[dict[str, Any]], asset_id: str) -> dict[str, Any]:
    for a in assets:
        if str(a.get("id") or "") == str(asset_id):
            return a
    return {}


def _classified_for(
    classified: list[ClassifiedAssetItem], asset_id: str
) -> ClassifiedAssetItem | None:
    for c in classified:
        if c.asset_id == str(asset_id):
            return c
    return None


def _processes_using_asset(response_data: dict[str, Any], asset_id: str) -> list[str]:
    out: list[str] = []
    aid = str(asset_id).strip()
    procs = response_data.get("business_processes", [])
    if not isinstance(procs, list):
        return out
    for p in procs:
        if not isinstance(p, dict):
            continue
        name = str(p.get("name") or "").strip()
        ids = p.get("used_asset_ids") or p.get("asset_ids") or []
        if not isinstance(ids, list):
            continue
        id_set = {str(x).strip() for x in ids if x is not None}
        if aid in id_set and name:
            out.append(name)
    return sorted(set(out))


def _text_mentions_asset(text: str, asset_id: str, asset_name: str) -> bool:
    t = _norm(text)
    if not t:
        return False
    if asset_id and _norm(asset_id) in t:
        return True
    if asset_name and len(asset_name.strip()) >= 3 and _norm(asset_name) in t:
        return True
    return False


def _incidents_for_asset(
    response_data: dict[str, Any], asset_id: str, asset_name: str
) -> list[str]:
    out: list[str] = []
    inc = response_data.get("incidents", [])
    if not isinstance(inc, list):
        return out
    for row in inc:
        if not isinstance(row, dict):
            continue
        summary = str(row.get("summary") or row.get("name") or "")
        details = str(row.get("details") or "")
        blob = f"{summary}\n{details}"
        if _text_mentions_asset(blob, asset_id, asset_name):
            line = summary.strip()
            if details.strip():
                line = f"{line}: {details.strip()}" if line else details.strip()
            if line:
                out.append(line)
    return out


def _access_matrix_hints(
    response_data: dict[str, Any], asset_id: str, asset_name: str
) -> list[str]:
    out: list[str] = []
    mx = response_data.get("access_matrix", [])
    if not isinstance(mx, list):
        return out
    for row in mx:
        if not isinstance(row, dict):
            continue
        res = str(row.get("resource") or "")
        note = str(row.get("note") or "")
        blob = f"{res}\n{note}"
        if _text_mentions_asset(blob, asset_id, asset_name):
            line = f"{res.strip()}" + (f" — {note.strip()}" if note.strip() else "")
            if line.strip():
                out.append(line.strip())
    return out


def _risk_rules(
    risk: RiskItem,
    ca: ClassifiedAssetItem | None,
    asset: dict[str, Any],
) -> list[str]:
    rules: list[str] = []
    if ca:
        rules.append(
            f"Актив классифицирован как среда «{ca.environment}» "
            f"(эффективная критичность: {ca.effective_criticality}, "
            f"исходная: {ca.original_criticality}, использований в процессах: {ca.usage_count})."
        )
        for n in ca.notes:
            if n.strip():
                rules.append(f"Примечание классификатора: {n.strip()}")
    else:
        rules.append("Классификация актива в отчёте не найдена (нештатные данные).")

    req_keys = asvc.RISK_TO_REQUIREMENT_KEYS.get(risk.risk_code, [])
    if req_keys:
        titles = [
            asvc.REQUIREMENT_DEFINITIONS[k]
            for k in req_keys
            if k in asvc.REQUIREMENT_DEFINITIONS
        ]
        if titles:
            rules.append(
                f"По коду риска «{risk.risk_code}» из каталога выбраны требования: "
                + "; ".join(titles)
                + ".",
            )
        else:
            rules.append(
                f"По коду риска «{risk.risk_code}» сопоставлены ключи требований: {', '.join(req_keys)}.",
            )

    rules.append(
        f"Уровень severity в отчёте: «{risk.severity}» (правило _risk_severity_for_asset / профиль актива).",
    )

    env = str(asset.get("network_zone") or "").strip()
    if env:
        rules.append(f"В анкете указана сетевая зона актива: {env}.")
    if asset.get("safety_critical") is True:
        rules.append("Актив помечен как safety-critical — усилены требования к доступности/безопасному состоянию.")
    return rules


def parse_risk_target_key(key: str) -> tuple[str, str] | None:
    m = re.match(r"^asset:(?P<aid>[^|]+)\|risk:(?P<code>.+)$", key.strip())
    if not m:
        return None
    return m.group("aid"), m.group("code")


def build_explanation_for_risk(
    *,
    target_key: str,
    response_data: dict[str, Any],
    report: AnalysisReport,
) -> ExplanationPayload | None:
    parsed = parse_risk_target_key(target_key)
    if not parsed:
        return None
    aid, rcode = parsed
    risk: RiskItem | None = None
    for r in report.risks:
        if r.asset_id == aid and r.risk_code == rcode:
            risk = r
            break
    if risk is None:
        return None

    ca = _classified_for(report.classified_assets, aid)
    arow = _asset_row(report.assets, aid)
    aname = str(arow.get("name") or "").strip() or aid
    env = ca.environment if ca else str(arow.get("environment") or "IT")

    processes = _processes_using_asset(response_data, aid)
    incidents = _incidents_for_asset(response_data, aid, aname)
    amx = _access_matrix_hints(response_data, aid, aname)
    rules = _risk_rules(risk, ca, arow)

    llm_text: str | None = None
    if report.ai_enrichment and report.ai_enrichment.risk_explanations:
        llm_text = (report.ai_enrichment.risk_explanations.get(target_key) or "").strip() or None

    src: Literal["rule_based", "hybrid", "ai_enrichment"] = (
        "hybrid" if llm_text else "rule_based"
    )
    if llm_text and not rules:
        src = "ai_enrichment"

    nz = str(arow.get("network_zone") or "").strip() or None
    ot_c: str | None = None
    comp: str | None = None
    if env == "OT":
        ot_c = ot_sup.ot_constraints_summary(arow)

    method = "catalog_mapping+llm_explanation" if llm_text else "catalog_mapping"

    return ExplanationPayload(
        kind="risk",
        target_key=target_key,
        title=f"Обоснование риска «{risk.title}» ({risk.risk_code})",
        asset=ExplanationAssetRef(id=aid, name=aname, environment=str(env)),
        processes=processes,
        incidents=incidents,
        access_matrix_hints=amx,
        rules=rules,
        source=src,
        method=method,
        llm_explanation=llm_text,
        confidence=1.0,
        network_zone=nz,
        ot_constraints=ot_c,
        compensating_measure=comp,
        requirement_title=None,
        measure_title=None,
        risk_code=risk.risk_code,
        risk_title=risk.title,
    )


def build_explanation_for_traceability(
    *,
    entry_index: int,
    response_data: dict[str, Any],
    report: AnalysisReport,
) -> ExplanationPayload | None:
    tm = report.traceability_map
    if tm is None or entry_index < 0 or entry_index >= len(tm.entries):
        return None
    entry: TraceabilityEntry = tm.entries[entry_index]

    aid = entry.asset_id
    arow = _asset_row(report.assets, aid)
    aname = entry.asset_name or str(arow.get("name") or "").strip() or aid
    ca = _classified_for(report.classified_assets, aid)
    env = entry.environment or (ca.environment if ca else "IT")

    processes = _processes_using_asset(response_data, aid)
    incidents = _incidents_for_asset(response_data, aid, aname)
    amx = _access_matrix_hints(response_data, aid, aname)

    rules: list[str] = [
        "Запись карты соответствия построена из цепочки rule-based: актив → риск → требование → мера (каталог).",
        f"Требование: «{entry.requirement_title}» (ключ: {entry.requirement_key or '—'}).",
        f"Мера: «{entry.measure_title}».",
    ]
    if ca:
        for n in ca.notes:
            if n.strip():
                rules.append(f"Классификация актива: {n.strip()}")
    if entry.ot_constraints:
        rules.append(f"Ограничения OT (rule-based): {entry.ot_constraints}.")
    if entry.compensating_measure:
        rules.append(
            "Выбрана компенсирующая мера вместо прямой IT-ориентированной (например MFA на устройстве или "
            "классический patch-management), см. текст меры и ограничения OT.",
        )
    elif ot_sup.is_compensating_measure(entry.measure_title):
        rules.append("Мера помечена как компенсирующая по префиксу в каталоге мер.")

    llm_link: str | None = None
    if report.ai_enrichment and report.ai_enrichment.link_explanations:
        llm_link = (report.ai_enrichment.link_explanations.get(f"link:{entry_index}") or "").strip() or None
    llm_text = (entry.explanation or "").strip() or llm_link

    if llm_text or entry.source == "hybrid":
        src_e: Literal["rule_based", "hybrid", "ai_enrichment"] = "hybrid"
    else:
        src_e = "rule_based"

    target_key = f"traceability:{entry_index}"

    return ExplanationPayload(
        kind="traceability",
        target_key=target_key,
        title="Обоснование записи карты соответствия (актив → риск → требование → мера)",
        asset=ExplanationAssetRef(id=aid, name=aname, environment=str(env)),
        processes=processes,
        incidents=incidents,
        access_matrix_hints=amx,
        rules=rules,
        source=src_e,
        method=entry.method,
        llm_explanation=llm_text,
        confidence=entry.confidence,
        network_zone=entry.network_zone,
        ot_constraints=entry.ot_constraints,
        compensating_measure=entry.compensating_measure or (
            entry.measure_title if ot_sup.is_compensating_measure(entry.measure_title) else None
        ),
        requirement_title=entry.requirement_title,
        measure_title=entry.measure_title,
        risk_code=entry.risk_code,
        risk_title=entry.risk_title,
    )


def build_explanation_payload(
    *,
    kind: Kind,
    response_data: dict[str, Any],
    report: AnalysisReport,
    risk_key: str | None = None,
    traceability_index: int | None = None,
) -> ExplanationPayload | None:
    out: ExplanationPayload | None = None
    if kind == "risk":
        if not risk_key:
            return None
        out = build_explanation_for_risk(
            target_key=risk_key,
            response_data=response_data,
            report=report,
        )
    else:
        if traceability_index is None:
            return None
        out = build_explanation_for_traceability(
            entry_index=traceability_index,
            response_data=response_data,
            report=report,
        )
    if out is not None:
        logger.info(
            "explanation built successfully kind=%s target=%s source=%s",
            kind,
            out.target_key,
            out.source,
        )
    return out
