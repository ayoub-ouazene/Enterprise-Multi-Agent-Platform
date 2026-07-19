"""Create IT access, hardware, incident, asset, and software structures.

Revision ID: 20260719_0009
Revises: 20260719_0008
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260719_0009"
down_revision: str | Sequence[str] | None = "20260719_0008"
branch_labels = None
depends_on = None


ENUMS = {
    "asset_status": ("available", "assigned", "reserved", "maintenance", "retired", "lost"),
    "it_access_type": ("software", "account", "password_reset", "account_unlock", "mfa"),
    "it_policy_decision": ("pending", "allowed", "denied", "approval_required"),
    "it_provisioning_status": ("pending", "prepared", "waiting_approval", "completed", "cancelled", "failed"),
    "hardware_assignment_status": ("pending", "inventory_checked", "asset_available", "waiting_budget", "waiting_procurement", "waiting_human", "prepared", "completed", "failed"),
    "it_incident_source": ("employee", "customer_support", "internal"),
    "it_request_category": ("it_information", "software_access", "password_reset", "account_unlock", "account_provisioning", "mfa_access", "hardware_request", "software_installation", "employee_incident", "external_customer_incident", "asset_assignment", "human_technician_escalation", "unsupported"),
    "it_impact_level": ("low", "medium", "high", "critical"),
    "it_urgency_level": ("low", "medium", "high", "critical"),
    "it_incident_status": ("new", "diagnosing", "waiting_user", "waiting_technician", "resolved", "closed", "failed"),
}


def enum(name: str):
    return postgresql.ENUM(*ENUMS[name], name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    for name in ENUMS:
        enum(name).create(bind, checkfirst=True)
    uuid = postgresql.UUID(as_uuid=True)
    def timestamps():
        return [sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)]
    op.create_table("assets",
        sa.Column("company_id", uuid, nullable=False), sa.Column("asset_code", sa.String(100), nullable=False),
        sa.Column("asset_type", sa.String(100), nullable=False), sa.Column("brand", sa.String(120), nullable=False),
        sa.Column("model", sa.String(160), nullable=False), sa.Column("serial_number", sa.String(255)),
        sa.Column("status", enum("asset_status"), server_default=sa.text("'available'"), nullable=False),
        sa.Column("assigned_employee_id", uuid), sa.Column("location", sa.String(255)),
        sa.Column("custom_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", uuid, nullable=False), *timestamps(),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_employee_id"], ["employees.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("company_id", "asset_code", name="uq_assets_company_code"),
        sa.UniqueConstraint("company_id", "serial_number", name="uq_assets_company_serial"))
    op.create_index("ix_assets_company_status_type", "assets", ["company_id", "status", "asset_type"])
    op.create_index("ix_assets_company_employee", "assets", ["company_id", "assigned_employee_id"])
    op.create_table("software_catalog",
        sa.Column("company_id", uuid, nullable=False), sa.Column("name", sa.String(255), nullable=False),
        sa.Column("access_type", sa.String(100), nullable=False),
        sa.Column("requires_manager_approval", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("requires_it_approval", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("license_limited", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("available_license_count", sa.Integer()), sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("custom_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", uuid, nullable=False), *timestamps(),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("company_id", "name", name="uq_software_catalog_company_name"))
    op.create_index("ix_software_catalog_company_active", "software_catalog", ["company_id", "is_active"])
    op.create_table("access_requests",
        sa.Column("request_id", uuid, nullable=False), sa.Column("company_id", uuid, nullable=False),
        sa.Column("employee_id", uuid, nullable=False), sa.Column("access_type", enum("it_access_type"), nullable=False),
        sa.Column("target_system", sa.String(255), nullable=False), sa.Column("requested_role", sa.String(255)),
        sa.Column("business_reason", sa.Text(), nullable=False),
        sa.Column("policy_decision", enum("it_policy_decision"), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("approval_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("provisioning_status", enum("it_provisioning_status"), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("custom_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)), *timestamps(),
        sa.ForeignKeyConstraint(["request_id"], ["business_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("request_id"))
    op.create_index("ix_access_requests_company_employee", "access_requests", ["company_id", "employee_id"])
    op.create_index("ix_access_requests_company_status", "access_requests", ["company_id", "provisioning_status"])
    op.create_table("hardware_requests",
        sa.Column("request_id", uuid, nullable=False), sa.Column("company_id", uuid, nullable=False), sa.Column("employee_id", uuid, nullable=False),
        sa.Column("asset_type", sa.String(100), nullable=False), sa.Column("requested_specification", sa.Text()), sa.Column("business_reason", sa.Text(), nullable=False),
        sa.Column("inventory_checked", sa.Boolean(), server_default=sa.text("false"), nullable=False), sa.Column("available_asset_id", uuid),
        sa.Column("estimated_cost", sa.Numeric(12, 2)), sa.Column("budget_validation_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("procurement_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("assignment_status", enum("hardware_assignment_status"), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("custom_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)), *timestamps(),
        sa.ForeignKeyConstraint(["request_id"], ["business_requests.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["available_asset_id"], ["assets.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("request_id"))
    op.create_index("ix_hardware_requests_company_employee", "hardware_requests", ["company_id", "employee_id"])
    op.create_index("ix_hardware_requests_company_status", "hardware_requests", ["company_id", "assignment_status"])
    op.create_table("it_incidents",
        sa.Column("request_id", uuid, nullable=False), sa.Column("company_id", uuid, nullable=False), sa.Column("reported_by_user_id", uuid, nullable=False),
        sa.Column("affected_employee_id", uuid), sa.Column("source", enum("it_incident_source"), nullable=False), sa.Column("category", enum("it_request_category"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False), sa.Column("symptoms", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("error_messages", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("impact", enum("it_impact_level"), server_default=sa.text("'medium'"), nullable=False),
        sa.Column("urgency", enum("it_urgency_level"), server_default=sa.text("'medium'"), nullable=False),
        sa.Column("diagnostic_steps", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False), sa.Column("resolution_summary", sa.Text()),
        sa.Column("incident_status", enum("it_incident_status"), server_default=sa.text("'new'"), nullable=False),
        sa.Column("requires_human_technician", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("custom_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False), sa.Column("resolved_at", sa.DateTime(timezone=True)), *timestamps(),
        sa.ForeignKeyConstraint(["request_id"], ["business_requests.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reported_by_user_id"], ["users.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["affected_employee_id"], ["employees.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("request_id"))
    op.create_index("ix_it_incidents_company_status", "it_incidents", ["company_id", "incident_status"])
    op.create_index("ix_it_incidents_company_reporter", "it_incidents", ["company_id", "reported_by_user_id"])


def downgrade() -> None:
    for table, indexes in (("it_incidents", ("ix_it_incidents_company_reporter", "ix_it_incidents_company_status")),
        ("hardware_requests", ("ix_hardware_requests_company_status", "ix_hardware_requests_company_employee")),
        ("access_requests", ("ix_access_requests_company_status", "ix_access_requests_company_employee")),
        ("software_catalog", ("ix_software_catalog_company_active",)),
        ("assets", ("ix_assets_company_employee", "ix_assets_company_status_type"))):
        for index in indexes:
            op.drop_index(index, table_name=table)
        op.drop_table(table)
    bind = op.get_bind()
    for name in reversed(tuple(ENUMS)):
        enum(name).drop(bind, checkfirst=True)
