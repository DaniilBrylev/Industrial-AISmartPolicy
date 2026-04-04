"""domain schema: departments, questionnaires, assets, policy, analysis

Revision ID: 20260404_0002
Revises: 20260404_0001
Create Date: 2026-04-04

Создаёт доменные таблицы и перечисления PostgreSQL для MVP ВКР.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260404_0002"
down_revision: Union[str, None] = "20260404_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    questionnaire_status = postgresql.ENUM(
        "draft",
        "submitted",
        "needs_revision",
        "approved",
        name="questionnaire_status",
    )
    validation_status = postgresql.ENUM(
        "pending",
        "valid",
        "invalid",
        name="validation_status",
    )
    environment_type = postgresql.ENUM("IT", "OT", name="environment_type")
    criticality_level = postgresql.ENUM(
        "low",
        "medium",
        "high",
        "critical",
        name="criticality_level",
    )
    risk_level = postgresql.ENUM(
        "low",
        "medium",
        "high",
        "critical",
        name="risk_level",
    )
    policy_document_status = postgresql.ENUM(
        "draft",
        "generated",
        "approved",
        "archived",
        name="policy_document_status",
    )

    questionnaire_status.create(bind, checkfirst=True)
    validation_status.create(bind, checkfirst=True)
    environment_type.create(bind, checkfirst=True)
    criticality_level.create(bind, checkfirst=True)
    risk_level.create(bind, checkfirst=True)
    policy_document_status.create(bind, checkfirst=True)

    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("manager_name", sa.String(length=255), nullable=False),
        sa.Column("contact_info", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "requirements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_requirements_code"),
    )

    op.create_table(
        "security_measures",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("measure_type", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_security_measures_code"),
    )

    op.create_table(
        "policy_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "generated",
                "approved",
                "archived",
                name="policy_document_status",
                create_type=False,
            ),
            server_default=sa.text("'draft'::policy_document_status"),
            nullable=False,
        ),
        sa.Column("current_version_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "questionnaires",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "submitted",
                "needs_revision",
                "approved",
                name="questionnaire_status",
                create_type=False,
            ),
            server_default=sa.text("'draft'::questionnaire_status"),
            nullable=False,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_questionnaires_department_id"), "questionnaires", ["department_id"], unique=False)

    op.create_table(
        "questionnaire_responses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("questionnaire_id", sa.Integer(), nullable=False),
        sa.Column(
            "response_data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "validation_status",
            postgresql.ENUM(
                "pending",
                "valid",
                "invalid",
                name="validation_status",
                create_type=False,
            ),
            server_default=sa.text("'pending'::validation_status"),
            nullable=False,
        ),
        sa.Column("validation_errors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["questionnaire_id"], ["questionnaires.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_questionnaire_responses_questionnaire_id"),
        "questionnaire_responses",
        ["questionnaire_id"],
        unique=False,
    )

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("asset_type", sa.String(length=128), nullable=False),
        sa.Column(
            "environment_type",
            postgresql.ENUM("IT", "OT", name="environment_type", create_type=False),
            nullable=False,
        ),
        sa.Column("owner_name", sa.String(length=255), nullable=False),
        sa.Column(
            "criticality",
            postgresql.ENUM(
                "low",
                "medium",
                "high",
                "critical",
                name="criticality_level",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("network_location", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assets_department_id"), "assets", ["department_id"], unique=False)

    op.create_table(
        "business_processes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("responsible_person", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_business_processes_department_id"),
        "business_processes",
        ["department_id"],
        unique=False,
    )

    op.create_table(
        "risks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("probability", sa.Numeric(6, 4), nullable=False),
        sa.Column("impact", sa.Numeric(6, 4), nullable=False),
        sa.Column(
            "risk_level",
            postgresql.ENUM(
                "low",
                "medium",
                "high",
                "critical",
                name="risk_level",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risks_asset_id"), "risks", ["asset_id"], unique=False)

    op.create_table(
        "analysis_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("questionnaire_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "classification_result",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("ai_explanation", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["questionnaire_id"], ["questionnaires.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_analysis_results_questionnaire_id"),
        "analysis_results",
        ["questionnaire_id"],
        unique=False,
    )
    op.create_index(op.f("ix_analysis_results_asset_id"), "analysis_results", ["asset_id"], unique=False)

    op.create_table(
        "policy_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("policy_document_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("generated_from_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("change_summary", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["policy_document_id"], ["policy_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_document_id",
            "version_number",
            name="uq_policy_versions_document_version",
        ),
    )
    op.create_index(
        op.f("ix_policy_versions_policy_document_id"),
        "policy_versions",
        ["policy_document_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_policy_documents_current_version_id",
        "policy_documents",
        "policy_versions",
        ["current_version_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_policy_documents_current_version_id", "policy_documents", type_="foreignkey")

    op.drop_index(op.f("ix_policy_versions_policy_document_id"), table_name="policy_versions")
    op.drop_table("policy_versions")

    op.drop_index(op.f("ix_analysis_results_asset_id"), table_name="analysis_results")
    op.drop_index(op.f("ix_analysis_results_questionnaire_id"), table_name="analysis_results")
    op.drop_table("analysis_results")

    op.drop_index(op.f("ix_risks_asset_id"), table_name="risks")
    op.drop_table("risks")

    op.drop_index(op.f("ix_business_processes_department_id"), table_name="business_processes")
    op.drop_table("business_processes")

    op.drop_index(op.f("ix_assets_department_id"), table_name="assets")
    op.drop_table("assets")

    op.drop_index(op.f("ix_questionnaire_responses_questionnaire_id"), table_name="questionnaire_responses")
    op.drop_table("questionnaire_responses")

    op.drop_index(op.f("ix_questionnaires_department_id"), table_name="questionnaires")
    op.drop_table("questionnaires")

    op.drop_table("policy_documents")

    op.drop_table("security_measures")

    op.drop_table("requirements")

    op.drop_table("departments")

    bind = op.get_bind()
    postgresql.ENUM(
        "draft", "generated", "approved", "archived", name="policy_document_status"
    ).drop(bind, checkfirst=True)
    postgresql.ENUM("low", "medium", "high", "critical", name="risk_level").drop(bind, checkfirst=True)
    postgresql.ENUM("low", "medium", "high", "critical", name="criticality_level").drop(
        bind, checkfirst=True
    )
    postgresql.ENUM("IT", "OT", name="environment_type").drop(bind, checkfirst=True)
    postgresql.ENUM("pending", "valid", "invalid", name="validation_status").drop(bind, checkfirst=True)
    postgresql.ENUM(
        "draft", "submitted", "needs_revision", "approved", name="questionnaire_status"
    ).drop(bind, checkfirst=True)
