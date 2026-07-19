"""Create company knowledge document metadata.

Revision ID: 20260719_0007
Revises: 20260718_0006
Create Date: 2026-07-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260719_0007"
down_revision: str | Sequence[str] | None = "20260718_0006"
branch_labels = None
depends_on = None

document_type = postgresql.ENUM(
    "policy",
    "procedure",
    "manual",
    "faq",
    "product_documentation",
    "troubleshooting_guide",
    "benefits_document",
    "internal_rule",
    "other",
    name="knowledge_document_type",
    create_type=False,
)
department_scope = postgresql.ENUM(
    "shared",
    "customer_support",
    "hr",
    "it",
    "finance",
    "procurement",
    name="knowledge_department_scope",
    create_type=False,
)
access_scope = postgresql.ENUM(
    "all_authenticated",
    "employees",
    "department_managers",
    "company_account",
    "internal_system",
    name="knowledge_access_scope",
    create_type=False,
)
document_status = postgresql.ENUM(
    "draft",
    "active",
    "inactive",
    "superseded",
    "deleted",
    name="knowledge_document_status",
    create_type=False,
)
ingestion_status = postgresql.ENUM(
    "pending",
    "processing",
    "completed",
    "failed",
    name="knowledge_ingestion_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        document_type,
        department_scope,
        access_scope,
        document_status,
        ingestion_status,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "knowledge_documents",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=True),
        sa.Column("document_type", document_type, nullable=False),
        sa.Column(
            "department_scope", postgresql.ARRAY(department_scope), nullable=False
        ),
        sa.Column("access_scope", access_scope, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            document_status,
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column(
            "supersedes_document_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("mime_type", sa.String(127), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column(
            "chunk_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "ingestion_status",
            ingestion_status,
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("ingestion_error_safe", sa.Text(), nullable=True),
        sa.Column(
            "custom_metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.CheckConstraint(
            "version > 0", name="ck_knowledge_documents_positive_version"
        ),
        sa.CheckConstraint(
            "file_size_bytes > 0", name="ck_knowledge_documents_positive_file_size"
        ),
        sa.CheckConstraint(
            "chunk_count >= 0", name="ck_knowledge_documents_nonnegative_chunks"
        ),
        sa.CheckConstraint(
            "cardinality(department_scope) > 0",
            name="ck_knowledge_documents_department_scope_nonempty",
        ),
        sa.CheckConstraint(
            "NOT is_active OR (status = 'active' AND ingestion_status = 'completed')",
            name="ck_knowledge_documents_active_completed",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_document_id"],
            ["knowledge_documents.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "supersedes_document_id", name="uq_knowledge_documents_supersedes"
        ),
    )
    for name, columns in (
        ("ix_knowledge_documents_company_status", ["company_id", "status"]),
        ("ix_knowledge_documents_company_active", ["company_id", "is_active"]),
        (
            "ix_knowledge_documents_company_ingestion",
            ["company_id", "ingestion_status"],
        ),
        ("ix_knowledge_documents_company_checksum", ["company_id", "checksum"]),
        ("ix_knowledge_documents_company_type", ["company_id", "document_type"]),
    ):
        op.create_index(name, "knowledge_documents", columns)


def downgrade() -> None:
    for name in (
        "ix_knowledge_documents_company_type",
        "ix_knowledge_documents_company_checksum",
        "ix_knowledge_documents_company_ingestion",
        "ix_knowledge_documents_company_active",
        "ix_knowledge_documents_company_status",
    ):
        op.drop_index(name, table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
    for enum_type in (
        ingestion_status,
        document_status,
        access_scope,
        department_scope,
        document_type,
    ):
        enum_type.drop(op.get_bind(), checkfirst=True)
