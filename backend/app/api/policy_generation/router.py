from fastapi import APIRouter

router = APIRouter(prefix="/policy-generation", tags=["policy_generation"])


@router.get("/", summary="Модуль генерации проекта политики ИБ (заготовка)")
def placeholder() -> dict[str, str]:
    return {"module": "policy_generation", "status": "planned"}
