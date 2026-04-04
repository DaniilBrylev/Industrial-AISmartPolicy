from fastapi import APIRouter

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/", summary="Модуль анализа и классификации (заготовка)")
def placeholder() -> dict[str, str]:
    return {"module": "analysis", "status": "planned"}
