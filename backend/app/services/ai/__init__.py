"""
Заготовка под будущий AI-сервис (OpenRouter и др.).

Здесь позже появятся клиент, промпты и оркестрация вызовов.
"""

from app.services.ai.client import AIClientProtocol, StubAIClient

__all__ = ["AIClientProtocol", "StubAIClient"]
