"""
Структура JSON response_data для модуля сбора (MVP).

Ключ revision_feedback задаётся сервером при возврате на доработку;
в теле PUT /response не передаётся (сохраняется из БД при обновлении).
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DepartmentProfileSection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    description: str = ""
    manager_name: str = ""
    contact_info: str = ""


class QuestionnaireResponseDataPayload(BaseModel):
    """
    Ожидаемая структура ответа анкеты (без revision_feedback).
    """

    model_config = ConfigDict(extra="ignore")

    department_profile: DepartmentProfileSection = Field(default_factory=DepartmentProfileSection)
    assets: list[Any] = Field(default_factory=list)
    business_processes: list[Any] = Field(default_factory=list)
    access_matrix: list[Any] = Field(default_factory=list)
    contractors: list[Any] = Field(default_factory=list)
    incidents: list[Any] = Field(default_factory=list)
    additional_notes: str = ""

    def to_stored_dict(self, revision_feedback: str | None) -> dict[str, Any]:
        data = self.model_dump(mode="python")
        if revision_feedback is not None:
            data["revision_feedback"] = revision_feedback
        return data


REQUIRED_TOP_LEVEL_KEYS = frozenset(
    {
        "department_profile",
        "assets",
        "business_processes",
        "access_matrix",
        "contractors",
        "incidents",
        "additional_notes",
    },
)

LIST_SECTION_KEYS = frozenset(
    {
        "assets",
        "business_processes",
        "access_matrix",
        "contractors",
        "incidents",
    },
)
