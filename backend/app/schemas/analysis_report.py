from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.validation import ValidationResult


class ClassifiedAssetItem(BaseModel):
    asset_id: str
    environment: Literal["IT", "OT"]
    original_criticality: str
    effective_criticality: str
    usage_count: int = Field(ge=0, description="Число процессов, ссылающихся на актив")
    notes: list[str] = Field(default_factory=list)


class RiskItem(BaseModel):
    asset_id: str
    risk_code: str
    title: str
    severity: Literal["low", "medium", "high", "critical"]


class AnalysisLinkItem(BaseModel):
    asset_id: str
    risk: str
    requirement: str
    measure: str


class TraceabilityEntry(BaseModel):
    """
    Одна запись карты соответствия (актив → риск → требование → мера).
    Формализует то, что уже задано rule-core и связями links, плюс опционально ИИ-объяснение.
    """

    model_config = ConfigDict(extra="ignore")

    asset_id: str
    asset_name: str = ""
    environment: Literal["IT", "OT"] | str = ""
    risk_code: str = ""
    risk_title: str = ""
    requirement_key: str = ""
    requirement_title: str = ""
    measure_title: str = ""
    source: Literal["rule_based", "hybrid"] = "rule_based"
    method: str = Field(
        default="catalog_mapping",
        description="Способ построения: catalog_mapping и/или llm_explanation",
    )
    explanation: str | None = None
    confidence: float | None = Field(default=1.0, ge=0.0, le=1.0)
    network_zone: str | None = Field(
        default=None,
        description="Зона сети актива (OT), если указана в анкете",
    )
    ot_constraints: str | None = Field(
        default=None,
        description="Кратко: ограничения OT (MFA/патчинг/safety), rule-based",
    )
    compensating_measure: str | None = Field(
        default=None,
        description="Текст компенсирующей меры, если мера выбрана как компенсирующая",
    )


class TraceabilityMap(BaseModel):
    """Карта прослеживаемости / соответствия для отчёта анализа (разд. 2 ВКР)."""

    entries: list[TraceabilityEntry] = Field(default_factory=list)


class AnalysisMeta(BaseModel):
    """Метаданные последнего успешного анализа для отслеживания актуальности (MVP)."""

    source_hash: str = Field(..., description="Отпечаток отслеживаемых секций анкеты")
    generated_at: str = Field(..., description="ISO-8601 UTC момент фиксации отчёта")
    tracked_sections: list[str] = Field(
        default_factory=list,
        description="Секции анкеты, вошедшие в source_hash",
    )


class AnalysisDiffPayload(BaseModel):
    """Результат сравнения сохранённого анализа с пересчётом по текущим данным (без сохранения)."""

    model_config = ConfigDict(extra="ignore")

    has_changes: bool = False
    summary: list[str] = Field(default_factory=list)
    added_risks: list[dict[str, Any]] = Field(default_factory=list)
    removed_risks: list[dict[str, Any]] = Field(default_factory=list)
    added_measures: list[str] = Field(default_factory=list)
    removed_measures: list[str] = Field(default_factory=list)
    added_traceability_entries: list[dict[str, Any]] = Field(default_factory=list)
    removed_traceability_entries: list[dict[str, Any]] = Field(default_factory=list)
    policy_sections_changed: list[str] = Field(default_factory=list)


class NlpEntityItem(BaseModel):
    """Сущность из неструктурированного текста анкеты (NER); не подменяет rule-based активы/риски."""

    model_config = ConfigDict(extra="ignore")

    type: str = Field(
        ...,
        description=(
            "Тип: asset, system, process, role, incident, contractor, department, "
            "requirement, network_zone, protective_measure, standard — или близкий синоним"
        ),
    )
    value: str = Field(..., description="Краткое текстовое значение сущности")
    source_field: str = Field(
        default="",
        description="Поле/фрагмент анкеты, откуда извлечено (например additional_notes, incidents[0])",
    )


class NlpRelationItem(BaseModel):
    """Связь между сущностями из текста (RE); справочная, не меняет links отчёта."""

    model_config = ConfigDict(extra="ignore")

    subject: str
    relation: str
    object: str
    source_field: str = Field(default="")


class AiAnalysisEnrichment(BaseModel):
    """
    Обогащение отчёта ИИ: explainability, резюме заметок, NLP (нормализация, NER, RE).
    Не изменяет rule-based поля отчёта.
    """

    risk_explanations: dict[str, str] = Field(default_factory=dict)
    link_explanations: dict[str, str] = Field(default_factory=dict)
    notes_summary: str | None = None
    normalized_text: dict[str, Any] | None = Field(
        None,
        description=(
            "Нормализованные текстовые фрагменты (ключи: additional_notes, incidents, "
            "contractors, access_matrix, business_processes, assets, department_profile и т.д.)"
        ),
    )
    entities: list[NlpEntityItem] | None = None
    relations: list[NlpRelationItem] | None = None
    llm_used: bool = False
    model: str | None = None
    generated_at: str | None = Field(None, description="ISO-8601 UTC")


class AnalysisReport(BaseModel):
    """Итог rules-based анализа; опционально — ai_enrichment после вызова LLM."""

    assets: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Снимок исходных активов (id, name, asset_type, criticality)",
    )
    classified_assets: list[ClassifiedAssetItem] = Field(default_factory=list)
    risks: list[RiskItem] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    measures: list[str] = Field(default_factory=list)
    links: list[AnalysisLinkItem] = Field(default_factory=list)
    warnings: list[str] = Field(
        default_factory=list,
        description="Предупреждения уровня анализа (не валидация)",
    )
    ai_enrichment: AiAnalysisEnrichment | None = None
    traceability_map: TraceabilityMap | None = Field(
        default=None,
        description="Явная карта соответствия актив → риск → требование → мера (надстройка над links)",
    )
    analysis_meta: AnalysisMeta | None = Field(
        default=None,
        description="Отпечаток входных данных на момент анализа (актуализация)",
    )


class QuestionnaireAnalyzeResponse(BaseModel):
    """
    Ответ POST /analyze: при невалидных данных — validation, report=null;
    при успехе — report, validation=null.
    """

    validation: ValidationResult | None = None
    report: AnalysisReport | None = None


class QuestionnaireAnalysisDiffResponse(BaseModel):
    """GET /questionnaires/{id}/analysis-diff: предпросмотр изменений до пересчёта."""

    analysis_stale: bool = Field(
        ...,
        description="True, если отслеживаемые секции анкеты разошлись с последним анализом",
    )
    stored_source_hash: str | None = Field(
        None,
        description="source_hash из последнего сохранённого analysis_result.analysis_meta",
    )
    projected_source_hash: str | None = Field(
        None,
        description="source_hash по текущему response_data (тем же правилам, что при analyze)",
    )
    diff: AnalysisDiffPayload


class ExplanationAssetRef(BaseModel):
    """Краткая ссылка на актив в explainability payload."""

    id: str
    name: str = ""
    environment: str = ""


class ExplanationPayload(BaseModel):
    """
    Нормализованное объяснение решения анализа (XAI MVP).
    Собирается из rule-based отчёта, traceability и ai_enrichment без генерации новых фактов.
    """

    kind: Literal["risk", "traceability"]
    target_key: str
    title: str
    asset: ExplanationAssetRef | None = None
    processes: list[str] = Field(default_factory=list)
    incidents: list[str] = Field(default_factory=list)
    access_matrix_hints: list[str] = Field(
        default_factory=list,
        description="Строки матрицы доступа, где упоминается актив",
    )
    rules: list[str] = Field(default_factory=list)
    source: Literal["rule_based", "hybrid", "ai_enrichment"] = "rule_based"
    method: str = ""
    llm_explanation: str | None = None
    confidence: float | None = None
    network_zone: str | None = None
    ot_constraints: str | None = None
    compensating_measure: str | None = None
    requirement_title: str | None = None
    measure_title: str | None = None
    risk_code: str | None = None
    risk_title: str | None = None


class ExplanationRequest(BaseModel):
    """POST /questionnaires/{id}/explanation"""

    kind: Literal["risk", "traceability"]
    risk_key: str | None = Field(
        None,
        description='Для kind=risk: ключ вида "asset:<id>|risk:<risk_code>"',
    )
    traceability_index: int | None = Field(
        None,
        ge=0,
        description="Для kind=traceability: индекс записи в traceability_map.entries (совпадает с links)",
    )
