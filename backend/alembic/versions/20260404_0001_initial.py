"""initial schema placeholder

Revision ID: 20260404_0001
Revises:
Create Date: 2026-04-04

Пустая начальная миграция. После добавления моделей выполните:
alembic revision --autogenerate -m "..."
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260404_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
