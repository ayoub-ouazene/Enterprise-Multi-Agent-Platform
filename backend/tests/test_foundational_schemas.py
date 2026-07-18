from datetime import UTC, datetime
from uuid import uuid4

from app.core.enums import ActorType
from app.departments.schemas import DepartmentCreate, DepartmentUpdate
from app.employees.schemas import EmployeeCreate, EmployeeUpdate
from app.users.models import User
from app.users.schemas import UserCreate, UserInternalRead, UserResponse, UserUpdate


def test_password_hash_never_appears_in_user_response_schema() -> None:
    now = datetime.now(UTC)
    user = User(
        id=uuid4(),
        company_id=uuid4(),
        email="manager@example.com",
        password_hash="not-a-real-password-hash",
        actor_type=ActorType.DEPARTMENT_MANAGER,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    internal_data = UserInternalRead.model_validate(user).model_dump()
    response_data = UserResponse.model_validate(user).model_dump()

    assert "password_hash" not in UserCreate.model_fields
    assert "password_hash" not in UserUpdate.model_fields
    assert "password_hash" not in internal_data
    assert "password_hash" not in response_data


def test_tenant_payload_schemas_do_not_accept_company_id() -> None:
    tenant_payload_schemas = (
        UserCreate,
        UserUpdate,
        DepartmentCreate,
        DepartmentUpdate,
        EmployeeCreate,
        EmployeeUpdate,
    )

    for schema in tenant_payload_schemas:
        assert "company_id" not in schema.model_fields
