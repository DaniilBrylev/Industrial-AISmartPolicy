from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Переменные окружения имеют приоритет над env_file (pydantic-settings).
    В Docker ключи OpenRouter задайте через compose environment / env_file в корне проекта.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Industrial AISmartPolicy API"
    debug: bool = False

    database_url: str = "postgresql+psycopg2://aisec:aisec_secret_change_me@localhost:5432/aisec_policy"

    # OpenRouter — env: OPENROUTER_API_KEY, OPENROUTER_MODEL
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    openrouter_timeout_seconds: float = 60.0
    openrouter_max_input_chars: int = 16000
    openrouter_http_referer: str = ""  # опционально для OpenRouter rankings
    openrouter_app_title: str = "Industrial AISmartPolicy"

    # Экспорт сгенерированных политик (DOCX)
    policy_export_dir: str = "var/generated_policies"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
