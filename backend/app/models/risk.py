from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RiskLevel
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.asset import Asset


class Risk(Base, TimestampMixin):
    __tablename__ = "risks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    probability: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    impact: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(
            RiskLevel,
            name="risk_level",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
        ),
        nullable=False,
    )

    asset: Mapped["Asset"] = relationship(back_populates="risks")
