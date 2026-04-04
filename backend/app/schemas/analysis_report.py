from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

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


class AnalysisReport(BaseModel):
    """Итог rules-based анализа анкеты (без ML)."""

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


class QuestionnaireAnalyzeResponse(BaseModel):
    """
    Ответ POST /analyze: при невалидных данных — validation, report=null;
    при успехе — report, validation=null.
    """

    validation: ValidationResult | None = None
    report: AnalysisReport | None = None
