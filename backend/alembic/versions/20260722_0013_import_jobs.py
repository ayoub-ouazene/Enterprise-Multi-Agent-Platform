"""Create import_jobs for onboarding.

Revision ID: 20260722_0013
Revises: 20260719_0012
Create Date: 2026-07-22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260722_0013"
down_revision: str | Sequence[str] | None = "20260719_0012"
branch_labels = None
depends_on = None

import_type_enum = postgresql.ENUM(
    "employees",
    "departments",
    "manager_assignments",
    "assets",
    "software_catalog",
    "budgets",
    "supplier_candidates",
    "company_holidays",
    "staffing_rules",
    name="import_type",
    create_type=False,
)

import_job_status_enum = postgresql.ENUM(
    "pending",
    "validating",
    "ready",
    "processing",
    "completed",
    "partially_completed",
    "failed",
    "cancelled",
    name="import_job_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    import_type_enum.create(bind, checkfirst=True)
    import_job_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "import_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_type", import_type_enum, nullable=False),
        sa.Column(
            "status",
            import_job_status_enum,
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "total_rows",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "valid_rows",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "invalid_rows",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "processed_rows",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column(
            "validation_report",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_import_jobs_company_status",
        "import_jobs",
        ["company_id", "status"],
    )
    op.create_index(
        "ix_import_jobs_company_type",
        "import_jobs",
        ["company_id", "import_type"],
    )
    op.create_index(
        "ix_import_jobs_checksum",
        "import_jobs",
        ["company_id", "import_type", "checksum"],
    )


def downgrade() -> None:
    op.drop_index("ix_import_jobs_checksum", table_name="import_jobs")
    op.drop_index("ix_import_jobs_company_type", table_name="import_jobs")
    op.drop_index("ix_import_jobs_company_status", table_name="import_jobs")
    op.drop_table("import_jobs")
    import_job_status_enum.drop(op.get_bind(), checkfirst=True)
    import_type_enum.drop(op.get_bind(), checkfirst=True)
