from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    """Одна ошибка или предупреждение проверки."""

    code: str = Field(..., min_length=1, description="Стабильный код для клиента/логов")
    field: str = Field(..., min_length=1, description="Логический путь к полю")
    message: str = Field(..., min_length=1, description="Человекочитаемое описание")


class ValidationResult(BaseModel):
    """Итог серверной валидации анкеты перед анализом."""

    is_valid: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
