"""Pydantic-схемы для API и сервисов."""

from app.schemas.analysis_report import (
    AnalysisLinkItem,
    AnalysisReport,
    ClassifiedAssetItem,
    QuestionnaireAnalyzeResponse,
    RiskItem,
)
from app.schemas.asset import AssetBase, AssetCreate, AssetRead, AssetUpdate
from app.schemas.common import DeleteStatusResponse
from app.schemas.business_process import (
    BusinessProcessBase,
    BusinessProcessCreate,
    BusinessProcessRead,
    BusinessProcessUpdate,
)
from app.schemas.department import (
    DepartmentBase,
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
)
from app.schemas.policy import (
    DiffChunk,
    PolicyDocumentBase,
    PolicyDocumentCreate,
    PolicyDocumentRead,
    PolicyDocumentUpdate,
    PolicySnapshotDiff,
    PolicyVersionBase,
    PolicyVersionCreate,
    PolicyVersionRead,
    PolicyVersionSummaryRead,
    PolicyVersionUpdate,
    QuestionnairePolicyGenerateResponse,
    QuestionnairePolicyVersioningInfo,
)
from app.schemas.questionnaire import (
    QuestionnaireBase,
    QuestionnaireCreate,
    QuestionnaireRead,
    QuestionnaireUpdate,
)
from app.schemas.questionnaire_collection import (
    QuestionnaireResponseRead,
    QuestionnaireResponseSave,
    QuestionnaireRevisionRequest,
    QuestionnaireStatusChangeResponse,
)
from app.schemas.validation import ValidationIssue, ValidationResult

__all__ = [
    "AnalysisLinkItem",
    "AnalysisReport",
    "ClassifiedAssetItem",
    "QuestionnaireAnalyzeResponse",
    "RiskItem",
    "DeleteStatusResponse",
    "AssetBase",
    "AssetCreate",
    "AssetRead",
    "AssetUpdate",
    "BusinessProcessBase",
    "BusinessProcessCreate",
    "BusinessProcessRead",
    "BusinessProcessUpdate",
    "DepartmentBase",
    "DepartmentCreate",
    "DepartmentRead",
    "DepartmentUpdate",
    "PolicyDocumentBase",
    "PolicyDocumentCreate",
    "PolicyDocumentRead",
    "PolicyDocumentUpdate",
    "DiffChunk",
    "PolicySnapshotDiff",
    "PolicyVersionBase",
    "PolicyVersionCreate",
    "PolicyVersionRead",
    "PolicyVersionSummaryRead",
    "PolicyVersionUpdate",
    "QuestionnairePolicyGenerateResponse",
    "QuestionnairePolicyVersioningInfo",
    "QuestionnaireBase",
    "QuestionnaireCreate",
    "QuestionnaireRead",
    "QuestionnaireUpdate",
    "QuestionnaireResponseRead",
    "QuestionnaireResponseSave",
    "QuestionnaireRevisionRequest",
    "QuestionnaireStatusChangeResponse",
    "ValidationIssue",
    "ValidationResult",
]
