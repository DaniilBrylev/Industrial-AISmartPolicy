from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str | bool]:
    llm_enabled = bool((settings.openrouter_api_key or "").strip())
    return {
        "status": "ok",
        "service": "backend",
        "llm_enabled": llm_enabled,
    }
