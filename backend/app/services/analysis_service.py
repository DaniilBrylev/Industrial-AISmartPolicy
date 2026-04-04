"""
Rules-based анализ и классификация данных анкеты (без ML).

Цепочка: актив → риск → требование → мера (справочники и правила в коде).
Результат дополнительно сохраняется в response_data['analysis_result'] (JSONB).
"""

from __future__ import annotations

import re
from typing import Any, Literal, cast

from sqlalchemy.orm import Session

from app.models.questionnaire_response import QuestionnaireResponse
from app.schemas.analysis_report import (
    AnalysisLinkItem,
    AnalysisReport,
    ClassifiedAssetItem,
    QuestionnaireAnalyzeResponse,
    RiskItem,
)
from app.schemas.validation import ValidationResult
from app.services import questionnaire_collection_service as qc
from app.services.validation_service import validate_questionnaire

# ---------------------------------------------------------------------------
# Классификация IT / OT (ключевые слова в name + asset_type)
# ---------------------------------------------------------------------------

_OT_PATTERN = re.compile(
    r"\b(scada|plc|hmi|dcs|industrial|production|ot\b|mes|кск|плк|асутп)\b",
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
    "OT_PRODUCTION_STOP": ["REQ_OT_AVAILABILITY", "REQ_MONITORING"],
    "OT_PROCESS_DISTURBANCE": ["REQ_OT_INTEGRITY", "REQ_ACCESS_CONTROL"],
    "OT_UNAUTHORIZED_ACCESS": ["REQ_ACCESS_CONTROL", "REQ_LOGGING"],
}

REQUIREMENT_DEFINITIONS: dict[str, str] = {
    "REQ_DATA_PROTECTION": "Защита конфиденциальных данных",
    "REQ_ACCESS_CONTROL": "Контроль доступа к информации и функциям",
    "REQ_LOGGING": "Журналирование и аудит событий безопасности",
    "REQ_AVAILABILITY": "Обеспечение доступности ИТ-сервисов",
    "REQ_MONITORING": "Мониторинг и выявление инцидентов",
    "REQ_OT_AVAILABILITY": "Отказоустойчивость и непрерывность технологических процессов",
    "REQ_OT_INTEGRITY": "Целостность технологических данных и управления",
}

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
}


# ---------------------------------------------------------------------------
# Публичные функции анализа
# ---------------------------------------------------------------------------


def classify_assets(response_data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Определяет среду (IT/OT) по текстовым признакам name и asset_type.
    Возвращает список словарей: asset_id, environment.
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
        text = f"{item.get('name', '')} {item.get('asset_type', '')}"
        env: Environment
        if _OT_PATTERN.search(text):
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
    """Формирует базовый набор рисков по среде и эффективной критичности."""
    _ = response_data  # зарезервировано для расширений (другие секции анкеты)
    risks: list[RiskItem] = []

    for ca in classified_assets:
        env = ca.environment
        c = ca.effective_criticality

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
        else:
            risks.append(
                RiskItem(
                    asset_id=ca.asset_id,
                    risk_code="OT_PRODUCTION_STOP",
                    title="Остановка производства",
                    severity=_risk_severity_for_asset(c, "critical"),
                )
            )
            risks.append(
                RiskItem(
                    asset_id=ca.asset_id,
                    risk_code="OT_PROCESS_DISTURBANCE",
                    title="Нарушение технологического процесса",
                    severity=_risk_severity_for_asset(c, "high"),
                )
            )
            risks.append(
                RiskItem(
                    asset_id=ca.asset_id,
                    risk_code="OT_UNAUTHORIZED_ACCESS",
                    title="Несанкционированное воздействие на OT",
                    severity=_risk_severity_for_asset(c, "high"),
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


def _asset_snapshot(response_data: dict[str, Any]) -> list[dict[str, Any]]:
    raw = response_data.get("assets", [])
    if not isinstance(raw, list):
        return []
    snap: list[dict[str, Any]] = []
    for a in raw:
        if not isinstance(a, dict):
            continue
        snap.append(
            {
                "id": a.get("id"),
                "name": a.get("name"),
                "asset_type": a.get("asset_type"),
                "criticality": a.get("criticality"),
            }
        )
    return snap


def _build_links(risks: list[RiskItem]) -> list[AnalysisLinkItem]:
    links: list[AnalysisLinkItem] = []
    for r in risks:
        req_keys = RISK_TO_REQUIREMENT_KEYS.get(r.risk_code, [])
        for rk in req_keys:
            title = REQUIREMENT_DEFINITIONS.get(rk)
            if not title:
                continue
            for meas in REQUIREMENT_TO_MEASURES.get(rk, []):
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
    risks = detect_risks(response_data, classified)
    req_titles = map_risks_to_requirements(risks)
    measures = map_requirements_to_measures(req_titles)
    links = _build_links(risks)

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


def _persist_report(row: QuestionnaireResponse, report: AnalysisReport, db: Session) -> None:
    data = dict(row.response_data) if isinstance(row.response_data, dict) else {}
    data["analysis_result"] = report.model_dump(mode="json")
    row.response_data = data
    db.add(row)
    db.commit()
    db.refresh(row)


def analyze_questionnaire(
    db: Session, questionnaire_id: int
) -> tuple[str | None, QuestionnaireAnalyzeResponse | None]:
    """
    Валидация → при успехе расчёт отчёта и запись в response_data.analysis_result.

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
    _persist_report(row, report, db)

    return None, QuestionnaireAnalyzeResponse(validation=None, report=report)
