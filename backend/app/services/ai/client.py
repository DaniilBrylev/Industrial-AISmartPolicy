from typing import Protocol, runtime_checkable


@runtime_checkable
class AIClientProtocol(Protocol):
    """Контракт для внешнего LLM/AI API (реализация на следующих этапах)."""

    async def complete(self, prompt: str, *, max_tokens: int = 1024) -> str: ...


class StubAIClient:
    """Заглушка до подключения реального провайдера."""

    async def complete(self, prompt: str, *, max_tokens: int = 1024) -> str:
        return ""
