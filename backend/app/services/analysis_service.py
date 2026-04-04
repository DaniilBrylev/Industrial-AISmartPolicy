"""
Rules-based анализ и классификация данных анкеты (без ML).

Цепочка: актив → риск → требование → мера (справочники и правила в коде).
Результат дополнительно сохраняется в response_data['analysis_result'] (JSONB).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Literal, cast

from sqlalchemy.orm import Session

from app.models.questionnaire_response import QuestionnaireResponse
from app.core.config import settings
from app.schemas.analysis_report import (
    AnalysisLinkItem,
    AnalysisMeta,
    AnalysisReport,
    ClassifiedAssetItem,
    QuestionnaireAnalyzeResponse,
    RiskItem,
    TraceabilityEntry,
    TraceabilityMap,
)
from app.schemas.validation import ValidationResult
from app.services import questionnaire_collection_service as qc
from app.services.policy_workflow_service import transition_after_analyze
from app.services.questionnaire_service import get_questionnaire
from app.services.analysis_ai_enrichment_service import enrich_analysis_report_with_ai
from app.services.analysis_source_hash import TRACKED_SECTIONS, compute_analysis_source_hash
from app.services.ai_service import AIService
from app.services.validation_service import validate_questionnaire
from app.services import analysis_ot_support as ot_sup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Классификация IT / OT (ключевые слова в name + asset_type)
# ---------------------------------------------------------------------------

_OT_PATTERN = re.compile(
    r"\b(scada|plc|hmi|dcs|industrial|production|ot\b|mes|кск|плк|асутп|"
    r"плк|контроллер|датчик|sensor|historian|телеметр|шлюз|gateway|"
    r"инженерн|операторск|технологическ|field\s*device|автоматик)\b",
    re.IGNORECASE,
)
_IT_PATTERN = re.compile(
    r"\b(server|database|\bdb\b|sql|web|www|api\b|workstation|laptop|"
    r"cloud|saas|email|ad\b|active\s*directory|kubernetes|docker)\b",
    re.IGNORECASE,
)

Environment = Literal["IT", "OT"]

# ---------------------------------------------------------------------------
# Критичность (порядок для сравнения и повышения)
# ---------------------------------------------------------------------------

_CRIT_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
_CRIT_NAMES = ("low", "medium", "high", "critical")


def _norm_crit(raw: str | None) -> str:
    if not raw or not isinstance(raw, str):
        return "low"
    v = raw.strip().lower()
    return v if v in _CRIT_ORDER else "low"


def _max_crit(a: str, b: str) -> str:
    return a if _CRIT_ORDER[a] >= _CRIT_ORDER[b] else b


def _bump_crit(c: str) -> str:
    i = min(_CRIT_ORDER[c] + 1, 3)
    return _CRIT_NAMES[i]


# ---------------------------------------------------------------------------
# Справочник рисков (код → человекочитаемо + базовая severity по критичности актива)
# ---------------------------------------------------------------------------

def _risk_severity_for_asset(crit: str, base: str) -> Literal["low", "medium", "high", "critical"]:
    """Поднимаем severity риска вместе с критичностью актива."""
    boost = _CRIT_ORDER.get(crit, 0)
    bases = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    idx = min(bases.get(base, 1) + (1 if boost >= 2 else 0), 3)
    return _CRIT_NAMES[idx]  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Карта: риск → требования → меры
# ---------------------------------------------------------------------------

RISK_TO_REQUIREMENT_KEYS: dict[str, list[str]] = {
    "IT_DATA_LEAK": ["REQ_DATA_PROTECTION", "REQ_LOGGING"],
    "IT_UNAUTHORIZED_ACCESS": ["REQ_ACCESS_CONTROL", "REQ_LOGGING"],
    "IT_AVAILABILITY": ["REQ_AVAILABILITY", "REQ_MONITORING"],
    "OT_PRODUCTION_STOP": ["REQ_OT_AVAILABILITY", "REQ_MONITORING", "REQ_OT_SAFE_STATE"],
    "OT_PROCESS_DISTURBANCE": ["REQ_OT_INTEGRITY", "REQ_ACCESS_CONTROL"],
    "OT_UNAUTHORIZED_ACCESS": ["REQ_ACCESS_CONTROL", "REQ_LOGGING"],
    "OT_SEGMENT_AVAILABILITY": ["REQ_OT_AVAILABILITY", "REQ_OT_SEGMENTATION"],
    "OT_CONTROLLER_COMPROMISE": ["REQ_OT_INTEGRITY", "REQ_OT_CHANGE_CONTROL"],
    "OT_SETPOINT_TAMPERING": ["REQ_OT_INTEGRITY", "REQ_OT_SAFE_STATE"],
    "OT_TELEMETRY_LOSS": ["REQ_MONITORING", "REQ_OT_AVAILABILITY"],
    "OT_CONTRACTOR_REMOTE": ["REQ_OT_REMOTE_ACCESS", "REQ_ACCESS_CONTROL"],
    "OT_IT_OT_LATERAL": ["REQ_OT_SEGMENTATION", "REQ_MONITORING"],
    "OT_LEGACY_NO_PATCH": ["REQ_OT_INTEGRITY", "REQ_OT_COMPENSATING"],
    "OT_SAFE_STATE_FAILURE": ["REQ_OT_SAFE_STATE", "REQ_OT_AVAILABILITY"],
}

REQUIREMENT_DEFINITIONS: dict[str, str] = {
    "REQ_DATA_PROTECTION": "Защита конфиденциальных данных",
    "REQ_ACCESS_CONTROL": "Контроль доступа к информации и функциям",
    "REQ_LOGGING": "Журналирование и аудит событий безопасности",
    "REQ_AVAILABILITY": "Обеспечение доступности ИТ-сервисов",
    "REQ_MONITORING": "Мониторинг и выявление инцидентов",
    "REQ_OT_AVAILABILITY": "Отказоустойчивость и непрерывность технологических процессов",
    "REQ_OT_INTEGRITY": "Целостность технологических данных и управления",
    "REQ_OT_SEGMENTATION": "Сегментация и изоляция технологического контура",
    "REQ_OT_REMOTE_ACCESS": "Безопасный удалённый доступ подрядчиков к OT",
    "REQ_OT_SAFE_STATE": "Безопасное состояние технологического оборудования",
    "REQ_OT_COMPENSATING": "Компенсирующие меры при ограничениях OT-активов",
    "REQ_OT_CHANGE_CONTROL": "Контроль изменений конфигураций АСУ ТП",
}

# Плоский справочник для обратной совместимости (агрегат measures в отчёте строится по связям).
REQUIREMENT_TO_MEASURES: dict[str, list[str]] = {
    "REQ_DATA_PROTECTION": [
        "Классификация данных и шифрование",
        "DLP-контроль каналов утечки",
    ],
    "REQ_ACCESS_CONTROL": [
        "RBAC / принцип наименьших привилегий",
        "Многофакторная аутентификация для критичных систем",
    ],
    "REQ_LOGGING": [
        "Централизованный сбор и хранение журналов",
        "Корреляция событий безопасности",
    ],
    "REQ_AVAILABILITY": [
        "Резервирование критичных компонентов",
        "Регламенты восстановления (RTO/RPO)",
    ],
    "REQ_MONITORING": [
        "Непрерывный мониторинг состояния и событий",
        "Оповещение ответственных лиц",
    ],
    "REQ_OT_AVAILABILITY": [
        "Резервирование и сегментация OT-сети",
        "Планы аварийного переключения",
    ],
    "REQ_OT_INTEGRITY": [
        "Контроль изменений в АСУ ТП",
        "Проверка целостности конфигураций",
    ],
    "REQ_OT_SEGMENTATION": [
        "Сегментация IT и OT (DMZ, межсетевые экраны)",
    ],
    "REQ_OT_REMOTE_ACCESS": [
        "Jump host / bastion для удалённой поддержки OT",
    ],
    "REQ_OT_SAFE_STATE": [
        "Процедуры перевода установки в безопасное состояние",
    ],
    "REQ_OT_COMPENSATING": [
        f"{ot_sup.COMPENSATING_PREFIX}Комплексный контроль ограничений OT",
    ],
    "REQ_OT_CHANGE_CONTROL": [
        "Версионирование проектов ПЛК и согласование изменений",
    ],
}


# ---------------------------------------------------------------------------
# Публичные функции анализа
# ---------------------------------------------------------------------------


def classify_assets(response_data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Rule-based IT/OT: имя, тип, network_zone, протоколы, safety-признаки (без LLM).
    """
    assets = response_data.get("assets", [])
    if not isinstance(assets, list):
        return []

    out: list[dict[str, Any]] = []
    for item in assets:
        if not isinstance(item, dict):
            continue
        aid = item.get("id")
        if aid is None:
            continue
        sid = str(aid).strip()
        if not sid:
            continue
        text = ot_sup.asset_extended_text(item)
        env: Environment
        ot_hits = 0
        if _OT_PATTERN.search(text):
            ot_hits += 1
        if ot_sup.has_ot_protocol_hint(item):
            ot_hits += 1
        if ot_sup.has_ot_zone_hint(item):
            ot_hits += 1
        if ot_sup.is_safety_critical(item):
            ot_hits += 1
        if ot_hits > 0:
            env = "OT"
        elif _IT_PATTERN.search(text):
            env = "IT"
        else:
            env = "IT"
        out.append({"asset_id": sid, "environment": env})
    return out


def _usage_counts(processes: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for p in processes:
        if not isinstance(p, dict):
            continue
        ids = p.get("used_asset_ids")
        if ids is None:
            ids = p.get("asset_ids")
        if not isinstance(ids, list):
            continue
        for ref in ids:
            if ref is None:
                continue
            k = str(ref).strip()
            counts[k] = counts.get(k, 0) + 1
    return counts


def _build_classified_with_criticality(
    response_data: dict[str, Any],
    base_classification: list[dict[str, Any]],
) -> list[ClassifiedAssetItem]:
    processes = response_data.get("business_processes", [])
    if not isinstance(processes, list):
        processes = []
    usage = _usage_counts(processes)

    env_by_id = {c["asset_id"]: c["environment"] for c in base_classification}
    assets = response_data.get("assets", [])
    if not isinstance(assets, list):
        assets = []

    items: list[ClassifiedAssetItem] = []
    for item in assets:
        if not isinstance(item, dict):
            continue
        aid = item.get("id")
        if aid is None:
            continue
        sid = str(aid).strip()
        if not sid:
            continue
        orig = _norm_crit(
            str(item.get("criticality", "")) if item.get("criticality") else None
        )
        env_raw = env_by_id.get(sid, "IT")
        env = cast(Environment, env_raw if env_raw in ("IT", "OT") else "IT")
        n_use = usage.get(sid, 0)
        eff = orig
        notes: list[str] = []

        if n_use == 0:
            notes.append(
                f'Актив "{sid}" не привязан ни к одному бизнес-процессу '
                "(рекомендуется уточнить карту процессов)"
            )

        if env == "OT" and n_use >= 1:
            eff = _max_crit(eff, "high")
            notes.append(
                "OT-актив участвует в процессе: применено правило минимальной критичности high"
            )

        if env == "OT" and ot_sup.is_safety_critical(item):
            eff = _max_crit(eff, "high")
            notes.append(
                "Safety-critical OT: эффективная критичность не ниже high (rule-based)"
            )

        if n_use > 1:
            eff = _bump_crit(eff)
            notes.append(
                f"Актив используется в {n_use} процессах: критичность повышена на один уровень"
            )

        items.append(
            ClassifiedAssetItem(
                asset_id=sid,
                environment=env,
                original_criticality=orig,
                effective_criticality=eff,
                usage_count=n_use,
                notes=notes,
            )
        )
    return items


def detect_risks(
    response_data: dict[str, Any],
    classified_assets: list[ClassifiedAssetItem],
) -> list[RiskItem]:
    """Формирует набор рисков по среде, критичности и OT-профилю актива / анкеты."""
    risks: list[RiskItem] = []
    asset_by_id = _assets_by_id(response_data)
    envs = [ca.environment for ca in classified_assets]
    remote_ot = ot_sup.response_suggests_remote_ot_access(response_data)
    it_ot = ot_sup.questionnaire_has_both_environments(envs)

    for ca in classified_assets:
        env = ca.environment
        c = ca.effective_criticality
        asset = asset_by_id.get(ca.asset_id, {})

        if env == "IT":
            risks.append(
                RiskItem(
                    asset_id=ca.asset_id,
                    risk_code="IT_DATA_LEAK",
                    title="Утечка данных",
                    severity=_risk_severity_for_asset(c, "medium"),
                )
            )
            risks.append(
                RiskItem(
                    asset_id=ca.asset_id,
                    risk_code="IT_UNAUTHORIZED_ACCESS",
                    title="Несанкционированный доступ",
                    severity=_risk_severity_for_asset(c, "high"),
                )
            )
            if c in ("high", "critical"):
                risks.append(
                    RiskItem(
                        asset_id=ca.asset_id,
                        risk_code="IT_AVAILABILITY",
                        title="Недоступность критичного ИТ-сервиса",
                        severity=_risk_severity_for_asset(c, "high"),
                    )
                )
            continue

        crit_ot = c
        if ot_sup.is_safety_critical(asset):
            crit_ot = _max_crit(crit_ot, "high")

        risks.append(
            RiskItem(
                asset_id=ca.asset_id,
                risk_code="OT_PRODUCTION_STOP",
                title="Остановка производства",
                severity=_risk_severity_for_asset(crit_ot, "critical"),
            )
        )
        risks.append(
            RiskItem(
                asset_id=ca.asset_id,
                risk_code="OT_PROCESS_DISTURBANCE",
                title="Нарушение технологического процесса",
                severity=_risk_severity_for_asset(crit_ot, "high"),
            )
        )
        risks.append(
            RiskItem(
                asset_id=ca.asset_id,
                risk_code="OT_UNAUTHORIZED_ACCESS",
                title="Несанкционированное воздействие на OT",
                severity=_risk_severity_for_asset(crit_ot, "high"),
            )
        )

        if ot_sup.is_ot_network_like(asset):
            risks.append(
                RiskItem(
                    asset_id=ca.asset_id,
                    risk_code="OT_SEGMENT_AVAILABILITY",
                    title="Нарушение доступности технологического сегмента",
                    severity=_risk_severity_for_asset(crit_ot, "high"),
                )
            )

        if ot_sup.is_plc_like(asset):
            risks.append(
                RiskItem(
                    asset_id=ca.asset_id,
                    risk_code="OT_CONTROLLER_COMPROMISE",
                    title="Компрометация ПЛК / контроллера",
                    severity=_risk_severity_for_asset(crit_ot, "critical"),
                )
            )

        if ot_sup.is_plc_like(asset) or ot_sup.is_scada_hmi_like(asset):
            risks.append(
                RiskItem(
                    asset_id=ca.asset_id,
                    risk_code="OT_SETPOINT_TAMPERING",
                    title="Несанкционированное изменение технологических уставок",
                    severity=_risk_severity_for_asset(crit_ot, "high"),
                )
            )

        if ot_sup.is_sensor_like(asset) or ot_sup.is_historian_like(asset):
            risks.append(
                RiskItem(
                    asset_id=ca.asset_id,
                    risk_code="OT_TELEMETRY_LOSS",
                    title="Потеря телеметрии / наблюдаемости",
                    severity=_risk_severity_for_asset(crit_ot, "medium"),
                )
            )

        if remote_ot and (
            ot_sup.is_engineering_station_like(asset)
            or ot_sup.is_scada_hmi_like(asset)
            or ot_sup.is_plc_like(asset)
            or ot_sup.is_ot_gateway_like(asset)
        ):
            risks.append(
                RiskItem(
                    asset_id=ca.asset_id,
                    risk_code="OT_CONTRACTOR_REMOTE",
                    title="Удалённый доступ подрядчика в OT-контур",
                    severity=_risk_severity_for_asset(crit_ot, "high"),
                )
            )

        if it_ot:
            risks.append(
                RiskItem(
                    asset_id=ca.asset_id,
                    risk_code="OT_IT_OT_LATERAL",
                    title="Lateral movement из IT в OT",
                    severity=_risk_severity_for_asset(crit_ot, "high"),
                )
            )

        if ot_sup.supports_patching(asset) is False:
            risks.append(
                RiskItem(
                    asset_id=ca.asset_id,
                    risk_code="OT_LEGACY_NO_PATCH",
                    title="Legacy OT без регулярного патчинга",
                    severity=_risk_severity_for_asset(crit_ot, "medium"),
                )
            )

        if ot_sup.is_safety_critical(asset):
            risks.append(
                RiskItem(
                    asset_id=ca.asset_id,
                    risk_code="OT_SAFE_STATE_FAILURE",
                    title="Отказ перевода процесса в безопасное состояние",
                    severity=_risk_severity_for_asset(crit_ot, "critical"),
                )
            )

    return risks


def map_risks_to_requirements(risks: list[RiskItem]) -> list[str]:
    keys: set[str] = set()
    for r in risks:
        keys.update(RISK_TO_REQUIREMENT_KEYS.get(r.risk_code, []))
    titles = {REQUIREMENT_DEFINITIONS[k] for k in keys if k in REQUIREMENT_DEFINITIONS}
    return sorted(titles)


def map_requirements_to_measures(requirement_titles: list[str]) -> list[str]:
    """По человекочитаемым названиям требований находит меры (обратный индекс по определениям)."""
    title_to_key = {v: k for k, v in REQUIREMENT_DEFINITIONS.items()}
    measures: set[str] = set()
    for title in requirement_titles:
        key = title_to_key.get(title)
        if not key:
            continue
        for m in REQUIREMENT_TO_MEASURES.get(key, []):
            measures.add(m)
    return sorted(measures)


def _assets_by_id(response_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    raw = response_data.get("assets", [])
    if not isinstance(raw, list):
        return out
    for a in raw:
        if isinstance(a, dict) and a.get("id") is not None:
            sid = str(a["id"]).strip()
            if sid:
                out[sid] = a
    return out


_ASSET_OPTIONAL_SNAPSHOT_KEYS = (
    "network_zone",
    "vendor",
    "protocols",
    "supports_mfa",
    "supports_patching",
    "availability_class",
    "safety_critical",
)


def _asset_snapshot(response_data: dict[str, Any]) -> list[dict[str, Any]]:
    raw = response_data.get("assets", [])
    if not isinstance(raw, list):
        return []
    snap: list[dict[str, Any]] = []
    for a in raw:
        if not isinstance(a, dict):
            continue
        row: dict[str, Any] = {
            "id": a.get("id"),
            "name": a.get("name"),
            "asset_type": a.get("asset_type"),
            "criticality": a.get("criticality"),
        }
        if a.get("owner") is not None:
            row["owner"] = a.get("owner")
        elif a.get("owner_name") is not None:
            row["owner"] = a.get("owner_name")
        for k in _ASSET_OPTIONAL_SNAPSHOT_KEYS:
            if k in a and a[k] is not None and a[k] != "":
                row[k] = a[k]
        snap.append(row)
    return snap


def _build_links(
    risks: list[RiskItem],
    response_data: dict[str, Any],
    classified_by_id: dict[str, ClassifiedAssetItem],
) -> list[AnalysisLinkItem]:
    assets = _assets_by_id(response_data)
    links: list[AnalysisLinkItem] = []
    for r in risks:
        req_keys = RISK_TO_REQUIREMENT_KEYS.get(r.risk_code, [])
        ca = classified_by_id.get(r.asset_id)
        env_raw = ca.environment if ca else "IT"
        env: Environment = cast(Environment, env_raw if env_raw in ("IT", "OT") else "IT")
        asset = assets.get(r.asset_id, {})
        for rk in req_keys:
            title = REQUIREMENT_DEFINITIONS.get(rk)
            if not title:
                continue
            mlist = ot_sup.measures_for_requirement_key(
                rk, environment=env, asset=asset
            )
            if not mlist:
                for meas in REQUIREMENT_TO_MEASURES.get(rk, []):
                    links.append(
                        AnalysisLinkItem(
                            asset_id=r.asset_id,
                            risk=r.title,
                            requirement=title,
                            measure=meas,
                        )
                    )
                continue
            for meas in mlist:
                links.append(
                    AnalysisLinkItem(
                        asset_id=r.asset_id,
                        risk=r.title,
                        requirement=title,
                        measure=meas,
                    )
                )
    return links


def build_analysis_report(response_data: dict[str, Any]) -> AnalysisReport:
    """Полный конвейер rules engine без обращения к БД."""
    base_cls = classify_assets(response_data)
    classified = _build_classified_with_criticality(response_data, base_cls)
    classified_by_id = {c.asset_id: c for c in classified}
    risks = detect_risks(response_data, classified)
    req_titles = map_risks_to_requirements(risks)
    links = _build_links(risks, response_data, classified_by_id)
    measures = sorted({ln.measure for ln in links if ln.measure})

    global_warnings: list[str] = []
    for ca in classified:
        for n in ca.notes:
            if "не привязан" in n:
                global_warnings.append(n)

    return AnalysisReport(
        assets=_asset_snapshot(response_data),
        classified_assets=classified,
        risks=risks,
        requirements=req_titles,
        measures=measures,
        links=links,
        warnings=sorted(set(global_warnings)),
    )


def _asset_row_by_id(assets: list[dict[str, Any]], asset_id: str) -> dict[str, Any]:
    for a in assets:
        if str(a.get("id") or "") == str(asset_id):
            return a
    return {}


def _asset_display_name(assets: list[dict[str, Any]], asset_id: str) -> str:
    for a in assets:
        if str(a.get("id") or "") != str(asset_id):
            continue
        name = str(a.get("name") or "").strip()
        return name if name else str(asset_id)
    return str(asset_id)


def _environment_for_asset(
    classified: list[ClassifiedAssetItem],
    asset_id: str,
) -> Literal["IT", "OT"] | str:
    for ca in classified:
        if ca.asset_id == str(asset_id):
            return ca.environment
    return ""


def _risk_for_link(risks: list[RiskItem], asset_id: str, risk_title: str) -> RiskItem | None:
    t = (risk_title or "").strip()
    for r in risks:
        if r.asset_id == str(asset_id) and r.title == t:
            return r
    return None


def build_traceability_map(report: AnalysisReport) -> TraceabilityMap:
    """
    Карта соответствия поверх уже посчитанного отчёта: по одной записи на элемент links.
    Не меняет rule-based данные; explanation подтягивается из ai_enrichment.link_explanations при наличии.
    """
    logger.info("traceability map build started")
    title_to_key = {v: k for k, v in REQUIREMENT_DEFINITIONS.items()}
    link_expl = (
        report.ai_enrichment.link_explanations
        if report.ai_enrichment is not None
        else {}
    )

    entries: list[TraceabilityEntry] = []
    explanations_attached = 0

    for idx, link in enumerate(report.links):
        expl = (link_expl.get(f"link:{idx}") or "").strip() or None
        if expl:
            explanations_attached += 1

        r_item = _risk_for_link(report.risks, link.asset_id, link.risk)
        risk_code = r_item.risk_code if r_item else ""
        risk_title = r_item.title if r_item else link.risk

        req_title = link.requirement.strip() if link.requirement else ""
        req_key = title_to_key.get(req_title, "")

        env = _environment_for_asset(report.classified_assets, link.asset_id)
        asset_name = _asset_display_name(report.assets, link.asset_id)
        arow = _asset_row_by_id(report.assets, link.asset_id)
        nz = str(arow.get("network_zone") or "").strip() or None
        ot_con: str | None = None
        if env == "OT":
            ot_con = ot_sup.ot_constraints_summary(arow)
        mtitle = link.measure.strip() if link.measure else ""
        comp_measure: str | None = mtitle if ot_sup.is_compensating_measure(mtitle) else None

        source: Literal["rule_based", "hybrid"] = "hybrid" if expl else "rule_based"
        method = (
            "catalog_mapping+llm_explanation"
            if expl
            else "catalog_mapping"
        )

        entries.append(
            TraceabilityEntry(
                asset_id=str(link.asset_id),
                asset_name=asset_name,
                environment=env,
                risk_code=risk_code,
                risk_title=risk_title,
                requirement_key=req_key,
                requirement_title=req_title,
                measure_title=mtitle,
                source=source,
                method=method,
                explanation=expl,
                confidence=1.0,
                network_zone=nz,
                ot_constraints=ot_con,
                compensating_measure=comp_measure,
            )
        )

    tm = TraceabilityMap(entries=entries)
    logger.info("traceability entries count=%s", len(entries))
    logger.info("traceability explanations attached=%s", explanations_attached)
    return tm


def _persist_report(row: QuestionnaireResponse, report: AnalysisReport, db: Session) -> None:
    old_rd = dict(row.response_data) if isinstance(row.response_data, dict) else {}
    data = dict(old_rd)
    data["analysis_result"] = report.model_dump(mode="json", exclude_none=True)
    data["analysis_stale"] = False
    q = get_questionnaire(db, row.questionnaire_id)
    if q is not None:
        transition_after_analyze(q, old_rd, data)
    row.response_data = data
    db.add(row)
    db.commit()
    db.refresh(row)


async def analyze_questionnaire(
    db: Session,
    questionnaire_id: int,
    *,
    ai: AIService | None = None,
) -> tuple[str | None, QuestionnaireAnalyzeResponse | None]:
    """
    Валидация → rule-based отчёт → опционально ai_enrichment → traceability_map → запись analysis_result.

    Returns:
        (error_code, None) при 404;
        (None, body) при 200: либо validation (невалидно), либо report (успех).
    """
    vcode, vresult = validate_questionnaire(db, questionnaire_id)
    if vcode == "questionnaire_not_found":
        return "questionnaire_not_found", None
    if vcode == "response_not_found":
        return "response_not_found", None
    assert vresult is not None

    if not vresult.is_valid:
        return None, QuestionnaireAnalyzeResponse(validation=vresult, report=None)

    outcome, row, _ = qc.get_questionnaire_response(db, questionnaire_id)
    if outcome != "ok" or row is None:
        return "response_not_found", None

    raw = row.response_data
    data = dict(raw) if isinstance(raw, dict) else {}
    report = build_analysis_report(data)
    if ai is not None:
        report = await enrich_analysis_report_with_ai(report, data, ai, settings)
    report = report.model_copy(
        update={"traceability_map": build_traceability_map(report)},
    )
    report = report.model_copy(
        update={
            "analysis_meta": AnalysisMeta(
                source_hash=compute_analysis_source_hash(data),
                generated_at=datetime.now(timezone.utc).isoformat(),
                tracked_sections=list(TRACKED_SECTIONS),
            ),
        },
    )
    _persist_report(row, report, db)

    return None, QuestionnaireAnalyzeResponse(validation=None, report=report)
