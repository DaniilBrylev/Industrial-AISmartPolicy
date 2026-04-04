"""policy_versions: source_hash, snapshot

Revision ID: 20260406_0003
Revises: 20260404_0002
Create Date: 2026-04-06

Версионирование политики: хеш источников и снимок сгенерированного policy_data.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260406_0003"
down_revision: Union[str, None] = "20260404_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "policy_versions",
        sa.Column("source_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "policy_versions",
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index(
        op.f("ix_policy_versions_source_hash"),
        "policy_versions",
        ["source_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_policy_versions_source_hash"), table_name="policy_versions")
    op.drop_column("policy_versions", "snapshot")
    op.drop_column("policy_versions", "source_hash")
