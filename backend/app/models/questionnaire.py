from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import QuestionnaireStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.analysis_result import AnalysisResult
    from app.models.department import Department
    from app.models.questionnaire_response import QuestionnaireResponse


class Questionnaire(Base, TimestampMixin):
    __tablename__ = "questionnaires"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[QuestionnaireStatus] = mapped_column(
        Enum(
            QuestionnaireStatus,
            name="questionnaire_status",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
        ),
        nullable=False,
        server_default=QuestionnaireStatus.draft.value,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    department: Mapped["Department"] = relationship(back_populates="questionnaires")
    responses: Mapped[list["QuestionnaireResponse"]] = relationship(
        back_populates="questionnaire",
        cascade="all, delete-orphan",
    )
    analysis_results: Mapped[list["AnalysisResult"]] = relationship(
        back_populates="questionnaire",
        cascade="all, delete-orphan",
    )
