from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CriticalityLevel, EnvironmentType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.analysis_result import AnalysisResult
    from app.models.department import Department
    from app.models.risk import Risk


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(128), nullable=False)
    environment_type: Mapped[EnvironmentType] = mapped_column(
        Enum(
            EnvironmentType,
            name="environment_type",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
        ),
        nullable=False,
    )
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    criticality: Mapped[CriticalityLevel] = mapped_column(
        Enum(
            CriticalityLevel,
            name="criticality_level",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
        ),
        nullable=False,
    )
    network_location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    department: Mapped["Department"] = relationship(back_populates="assets")
    risks: Mapped[list["Risk"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
    )
    analysis_results: Mapped[list["AnalysisResult"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
    )
