import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.policy_service import PolicyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

_policy_service = PolicyService()


@router.get("/policies/{questionnaire_id}")
def download_questionnaire_policy_docx(questionnaire_id: int) -> FileResponse:
    """Скачивание последнего сгенерированного DOCX для анкеты."""
    path = _policy_service.docx_path(questionnaire_id)
    if not path.is_file():
        logger.warning("Policy DOCX not found: %s", path)
        raise HTTPException(status_code=404, detail="Policy file not found; run generate-policy first")
    fname = _policy_service.docx_filename(questionnaire_id)
    return FileResponse(
        path,
        filename=fname,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
