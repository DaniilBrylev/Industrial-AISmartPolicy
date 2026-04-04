from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PolicyDocumentStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.policy_version import PolicyVersion


class PolicyDocument(Base, TimestampMixin):
    __tablename__ = "policy_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[PolicyDocumentStatus] = mapped_column(
        Enum(
            PolicyDocumentStatus,
            name="policy_document_status",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
        ),
        nullable=False,
        server_default=PolicyDocumentStatus.draft.value,
    )
    current_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("policy_versions.id", use_alter=True, name="fk_policy_documents_current_version_id"),
        nullable=True,
    )

    versions: Mapped[list["PolicyVersion"]] = relationship(
        "PolicyVersion",
        back_populates="policy_document",
        foreign_keys="PolicyVersion.policy_document_id",
        cascade="all, delete-orphan",
    )
    current_version: Mapped["PolicyVersion | None"] = relationship(
        "PolicyVersion",
        foreign_keys=[current_version_id],
        remote_side="PolicyVersion.id",
        post_update=True,
    )
