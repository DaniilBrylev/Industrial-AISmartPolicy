import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.enums import QuestionnaireStatus
from app.schemas.common import DeleteStatusResponse
from app.schemas.questionnaire import QuestionnaireCreate, QuestionnaireRead, QuestionnaireUpdate
from app.schemas.questionnaire_collection import (
    QuestionnaireResponseRead,
    QuestionnaireResponseSave,
    QuestionnaireRevisionRequest,
    QuestionnaireStatusChangeResponse,
)

from app.schemas.analysis_report import QuestionnaireAnalyzeResponse
from app.schemas.policy import (
    QuestionnairePolicyGenerateResponse,
    QuestionnairePolicyVersioningInfo,
)
from app.schemas.validation import ValidationResult
from app.services import analysis_service
from app.services import policy_document_service
from app.services.ai_service import AIService, get_ai_service
from app.services.policy_service import PolicyService, get_policy_service, normalize_analysis_result
from app.services import questionnaire_collection_service as qc
from app.services import questionnaire_service
from app.services import validation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/questionnaires", tags=["questionnaires"])


def _http_for_collection(
    outcome: str,
    details: list[str],
    *,
    default_detail: str,
) -> None:
    if outcome == "ok":
        return
    if outcome == "questionnaire_not_found":
        raise HTTPException(status_code=404, detail="Questionnaire not found")
    if outcome == "response_not_found":
        raise HTTPException(status_code=404, detail="Questionnaire response not found")
    if outcome == "forbidden_approved":
        raise HTTPException(
            status_code=409,
            detail="Cannot modify responses for an approved questionnaire",
        )
    if outcome == "forbidden_submitted":
        raise HTTPException(
            status_code=409,
            detail="Cannot modify responses while questionnaire is submitted",
        )
    if outcome == "invalid_transition":
        raise HTTPException(
            status_code=409,
            detail=details[0] if details else "Invalid status transition",
        )
    if outcome == "validation_error":
        raise HTTPException(
            status_code=400,
            detail={"errors": details} if details else "Validation failed",
        )
    raise HTTPException(status_code=400, detail=default_detail)


@router.get("", response_model=list[QuestionnaireRead])
def list_questionnaires(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    department_id: int | None = Query(None, description="Фильтр по подразделению"),
    status: QuestionnaireStatus | None = Query(None, description="Фильтр по статусу"),
) -> list[QuestionnaireRead]:
    return questionnaire_service.list_questionnaires(
        db,
        skip=skip,
        limit=limit,
        department_id=department_id,
        status=status,
    )


@router.post("", response_model=QuestionnaireRead, status_code=201)
def create_questionnaire(
    payload: QuestionnaireCreate,
    db: Session = Depends(get_db),
) -> QuestionnaireRead:
    obj = questionnaire_service.create_questionnaire(db, payload)
    if obj is None:
        raise HTTPException(status_code=404, detail="Department not found")
    return obj


@router.get("/{questionnaire_id}/response", response_model=QuestionnaireResponseRead)
def get_questionnaire_response(
    questionnaire_id: int,
    db: Session = Depends(get_db),
) -> QuestionnaireResponseRead:
    outcome, row, details = qc.get_questionnaire_response(db, questionnaire_id)
    _http_for_collection(outcome, details, default_detail="Failed to load response")
    assert row is not None
    return row


@router.put("/{questionnaire_id}/response", response_model=QuestionnaireResponseRead)
def put_questionnaire_response(
    questionnaire_id: int,
    payload: QuestionnaireResponseSave,
    db: Session = Depends(get_db),
) -> QuestionnaireResponseRead:
    outcome, row, details = qc.save_questionnaire_response(
        db, questionnaire_id, payload
    )
    _http_for_collection(outcome, details, default_detail="Failed to save response")
    assert row is not None
    return row


@router.post("/{questionnaire_id}/validate", response_model=ValidationResult)
def validate_questionnaire_endpoint(
    questionnaire_id: int,
    db: Session = Depends(get_db),
) -> ValidationResult:
    code, result = validation_service.validate_questionnaire(db, questionnaire_id)
    if code == "questionnaire_not_found":
        raise HTTPException(status_code=404, detail="Questionnaire not found")
    if code == "response_not_found":
        raise HTTPException(status_code=404, detail="Questionnaire response not found")
    assert result is not None
    return result


@router.post(
    "/{questionnaire_id}/analyze",
    response_model=QuestionnaireAnalyzeResponse,
)
def analyze_questionnaire_endpoint(
    questionnaire_id: int,
    db: Session = Depends(get_db),
) -> QuestionnaireAnalyzeResponse:
    code, body = analysis_service.analyze_questionnaire(db, questionnaire_id)
    if code == "questionnaire_not_found":
        raise HTTPException(status_code=404, detail="Questionnaire not found")
    if code == "response_not_found":
        raise HTTPException(status_code=404, detail="Questionnaire response not found")
    assert body is not None
    return body


@router.post(
    "/{questionnaire_id}/generate-policy",
    response_model=QuestionnairePolicyGenerateResponse,
)
async def generate_questionnaire_policy(
    questionnaire_id: int,
    db: Session = Depends(get_db),
    ai: AIService = Depends(get_ai_service),
    policy_svc: PolicyService = Depends(get_policy_service),
    policy_document_id: int | None = Query(
        None,
        description="Если указан — создать/обновить версию PolicyVersion при изменении источников",
    ),
) -> QuestionnairePolicyGenerateResponse:
    outcome, row, _ = qc.get_questionnaire_response(db, questionnaire_id)
    if outcome == "questionnaire_not_found":
        raise HTTPException(status_code=404, detail="Questionnaire not found")
    if outcome == "response_not_found":
        raise HTTPException(status_code=404, detail="Questionnaire response not found")
    assert row is not None

    rd = row.response_data
    if not isinstance(rd, dict):
        rd = {}
    ar = rd.get("analysis_result")
    analysis_dict = normalize_analysis_result(ar)
    structure = policy_svc.build_policy_structure(rd, ar)
    try:
        policy = await policy_svc.generate_policy_text(structure, ai)
    except Exception as e:  # noqa: BLE001
        logger.exception("generate_policy_text failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Policy text generation failed",
        ) from e

    html_preview = policy_svc.render_html_preview(policy)
    out_path = policy_svc.docx_path(questionnaire_id)
    try:
        policy_svc.export_docx(policy, str(out_path))
    except Exception as e:  # noqa: BLE001
        logger.exception("export_docx failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to export DOCX",
        ) from e

    download_url = f"/api/files/policies/{questionnaire_id}"

    versioning: QuestionnairePolicyVersioningInfo | None = None
    if policy_document_id is not None:
        status, ver, src_hash = policy_document_service.create_new_version_if_needed(
            db,
            questionnaire_id=questionnaire_id,
            policy_document_id=policy_document_id,
            policy_data=policy,
            response_data=rd,
            analysis_result=analysis_dict,
        )
        versioning = QuestionnairePolicyVersioningInfo(
            status=status,
            version_id=ver.id if ver else None,
            version_number=ver.version_number if ver else None,
            source_hash=src_hash or None,
        )

    logger.info(
        "Policy generated for questionnaire_id=%s path=%s versioning=%s",
        questionnaire_id,
        out_path,
        versioning.status if versioning else None,
    )
    return QuestionnairePolicyGenerateResponse(
        html_preview=html_preview,
        download_url=download_url,
        versioning=versioning,
    )


@router.post(
    "/{questionnaire_id}/submit",
    response_model=QuestionnaireStatusChangeResponse,
)
def submit_questionnaire(
    questionnaire_id: int,
    db: Session = Depends(get_db),
) -> QuestionnaireStatusChangeResponse:
    outcome, q, details = qc.submit_questionnaire(db, questionnaire_id)
    if outcome == "validation_error":
        raise HTTPException(
            status_code=400,
            detail={"errors": details} if details else "Submit validation failed",
        )
    _http_for_collection(outcome, details, default_detail="Submit failed")
    assert q is not None
    return QuestionnaireStatusChangeResponse(
        questionnaire_id=q.id,
        status=q.status,
        message=qc.status_change_message(q.status),
    )


@router.post(
    "/{questionnaire_id}/return-for-revision",
    response_model=QuestionnaireStatusChangeResponse,
)
def return_questionnaire_for_revision(
    questionnaire_id: int,
    payload: QuestionnaireRevisionRequest,
    db: Session = Depends(get_db),
) -> QuestionnaireStatusChangeResponse:
    outcome, q, details = qc.return_questionnaire_for_revision(
        db, questionnaire_id, payload.reason
    )
    _http_for_collection(outcome, details, default_detail="Return for revision failed")
    assert q is not None
    return QuestionnaireStatusChangeResponse(
        questionnaire_id=q.id,
        status=q.status,
        message=qc.status_change_message(q.status),
    )


@router.post(
    "/{questionnaire_id}/approve",
    response_model=QuestionnaireStatusChangeResponse,
)
def approve_questionnaire(
    questionnaire_id: int,
    db: Session = Depends(get_db),
) -> QuestionnaireStatusChangeResponse:
    outcome, q, details = qc.approve_questionnaire(db, questionnaire_id)
    _http_for_collection(outcome, details, default_detail="Approve failed")
    assert q is not None
    return QuestionnaireStatusChangeResponse(
        questionnaire_id=q.id,
        status=q.status,
        message=qc.status_change_message(q.status),
    )


@router.post(
    "/{questionnaire_id}/reopen-draft",
    response_model=QuestionnaireStatusChangeResponse,
)
def reopen_questionnaire_draft(
    questionnaire_id: int,
    db: Session = Depends(get_db),
) -> QuestionnaireStatusChangeResponse:
    outcome, q, details = qc.reopen_questionnaire_draft(db, questionnaire_id)
    _http_for_collection(outcome, details, default_detail="Reopen draft failed")
    assert q is not None
    return QuestionnaireStatusChangeResponse(
        questionnaire_id=q.id,
        status=q.status,
        message=qc.status_change_message(q.status),
    )


@router.get("/{questionnaire_id}", response_model=QuestionnaireRead)
def get_questionnaire(
    questionnaire_id: int,
    db: Session = Depends(get_db),
) -> QuestionnaireRead:
    obj = questionnaire_service.get_questionnaire(db, questionnaire_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Questionnaire not found")
    return obj


@router.put("/{questionnaire_id}", response_model=QuestionnaireRead)
def update_questionnaire(
    questionnaire_id: int,
    payload: QuestionnaireUpdate,
    db: Session = Depends(get_db),
) -> QuestionnaireRead:
    obj = questionnaire_service.update_questionnaire(db, questionnaire_id, payload)
    if obj is None:
        raise HTTPException(status_code=404, detail="Questionnaire not found")
    return obj


@router.delete("/{questionnaire_id}", response_model=DeleteStatusResponse)
def delete_questionnaire(
    questionnaire_id: int,
    db: Session = Depends(get_db),
) -> DeleteStatusResponse:
    ok = questionnaire_service.delete_questionnaire(db, questionnaire_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Questionnaire not found")
    return DeleteStatusResponse(message="Questionnaire deleted")
