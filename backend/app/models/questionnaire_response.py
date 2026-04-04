from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ValidationStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.questionnaire import Questionnaire


class QuestionnaireResponse(Base, TimestampMixin):
    __tablename__ = "questionnaire_responses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    questionnaire_id: Mapped[int] = mapped_column(
        ForeignKey("questionnaires.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    response_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    validation_status: Mapped[ValidationStatus] = mapped_column(
        Enum(
            ValidationStatus,
            name="validation_status",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
        ),
        nullable=False,
        server_default=ValidationStatus.pending.value,
    )
    validation_errors: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)

    questionnaire: Mapped["Questionnaire"] = relationship(back_populates="responses")
