"""Create foundational company, user, department, and employee tables.

Revision ID: 20260716_0001
Revises:
Create Date: 2026-07-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260716_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


actor_type_enum = postgresql.ENUM(
    "company",
    "external_user",
    "employee",
    "department_manager",
    name="actor_type",
    create_type=False,
)
department_type_enum = postgresql.ENUM(
    "customer_support",
    "hr",
    "it",
    "finance",
    "procurement",
    name="department_type",
    create_type=False,
)
employment_status_enum = postgresql.ENUM(
    "active",
    "inactive",
    "on_leave",
    "terminated",
    name="employment_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    actor_type_enum.create(bind, checkfirst=True)
    department_type_enum.create(bind, checkfirst=True)
    employment_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "companies",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "custom_data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id", name="pk_companies"),
        sa.UniqueConstraint("slug", name="uq_companies_slug"),
    )
    op.create_index("ix_companies_is_active", "companies", ["is_active"])

    op.create_table(
        "users",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("actor_type", actor_type_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_users_company_id_companies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("company_id", "email", name="uq_users_company_email"),
    )
    op.create_index("ix_users_company_id", "users", ["company_id"])
    op.create_index(
        "ix_users_company_actor_type",
        "users",
        ["company_id", "actor_type"],
    )

    op.create_table(
        "departments",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("department_type", department_type_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "custom_data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_departments_company_id_companies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_departments"),
        sa.UniqueConstraint(
            "company_id",
            "department_type",
            name="uq_departments_company_type",
        ),
    )
    op.create_index("ix_departments_company_id", "departments", ["company_id"])
    op.create_index(
        "ix_departments_company_active",
        "departments",
        ["company_id", "is_active"],
    )

    op.create_table(
        "employees",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("employee_code", sa.String(length=100), nullable=False),
        sa.Column("job_title", sa.String(length=160), nullable=True),
        sa.Column("manager_employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "employment_status",
            employment_status_enum,
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "custom_data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_employees_company_id_companies",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_employees_department_id_departments",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["manager_employee_id"],
            ["employees.id"],
            name="fk_employees_manager_id_employees",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_employees_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_employees"),
        sa.UniqueConstraint(
            "company_id",
            "employee_code",
            name="uq_employees_company_code",
        ),
        sa.UniqueConstraint("user_id", name="uq_employees_user_id"),
    )
    op.create_index("ix_employees_company_id", "employees", ["company_id"])
    op.create_index("ix_employees_department_id", "employees", ["department_id"])
    op.create_index(
        "ix_employees_manager_id",
        "employees",
        ["manager_employee_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_employees_manager_id", table_name="employees")
    op.drop_index("ix_employees_department_id", table_name="employees")
    op.drop_index("ix_employees_company_id", table_name="employees")
    op.drop_table("employees")

    op.drop_index("ix_departments_company_active", table_name="departments")
    op.drop_index("ix_departments_company_id", table_name="departments")
    op.drop_table("departments")

    op.drop_index("ix_users_company_actor_type", table_name="users")
    op.drop_index("ix_users_company_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_companies_is_active", table_name="companies")
    op.drop_table("companies")

    employment_status_enum.drop(op.get_bind(), checkfirst=True)
    department_type_enum.drop(op.get_bind(), checkfirst=True)
    actor_type_enum.drop(op.get_bind(), checkfirst=True)
