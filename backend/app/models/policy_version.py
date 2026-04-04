from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.policy_document import PolicyDocument


class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    __table_args__ = (
        UniqueConstraint(
            "policy_document_id",
            "version_number",
            name="uq_policy_versions_document_version",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    policy_document_id: Mapped[int] = mapped_column(
        ForeignKey("policy_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    generated_from_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    change_summary: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    policy_document: Mapped["PolicyDocument"] = relationship(
        "PolicyDocument",
        back_populates="versions",
        foreign_keys=[policy_document_id],
    )
