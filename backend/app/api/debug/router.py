"""
Отладочные эндпоинты. GET /api/debug/llm-test — проверка доступа к OpenRouter.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.services.ai_service import AIService, get_ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/llm-test")
async def llm_test(ai: AIService = Depends(get_ai_service)) -> dict[str, str | bool]:
    """
    Минимальный запрос к LLM (ping). Убедитесь, что OPENROUTER_API_KEY задан в окружении.
    """
    if not (settings.openrouter_api_key or "").strip():
        logger.error("llm-test: OPENROUTER_API_KEY отсутствует")
        raise HTTPException(
            status_code=503,
            detail="OPENROUTER_API_KEY не настроен",
        )
    try:
        reply = await ai.call_llm(
            "You are a terse assistant. Reply with a single short word or phrase only.",
            'Ответь одним словом: "pong" (латиницей), без пояснений.',
        )
        return {"ok": True, "reply": reply.strip()}
    except Exception as e:  # noqa: BLE001 — отдаём клиенту причину
        logger.exception("llm-test: вызов OpenRouter не удался: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"OpenRouter error: {e!s}",
        ) from e
