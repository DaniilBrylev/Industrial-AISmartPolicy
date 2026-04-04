from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.business_process import BusinessProcess
    from app.models.questionnaire import Questionnaire


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    manager_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_info: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    questionnaires: Mapped[list["Questionnaire"]] = relationship(
        back_populates="department",
        cascade="all, delete-orphan",
    )
    assets: Mapped[list["Asset"]] = relationship(
        back_populates="department",
        cascade="all, delete-orphan",
    )
    business_processes: Mapped[list["BusinessProcess"]] = relationship(
        back_populates="department",
        cascade="all, delete-orphan",
    )
