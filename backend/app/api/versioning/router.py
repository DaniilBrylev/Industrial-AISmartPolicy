from fastapi import APIRouter

router = APIRouter(prefix="/versioning", tags=["versioning"])


@router.get("/", summary="Модуль версионирования документа (заготовка)")
def placeholder() -> dict[str, str]:
    return {"module": "versioning", "status": "planned"}
