import asyncio
from uuid import uuid4

import pytest

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionContext
from app.departments.exceptions import DepartmentContextMismatchError
from app.departments.registry import build_default_department_registry


def context(department_type: DepartmentType) -> DepartmentExecutionContext:
    return DepartmentExecutionContext(
        request_id=uuid4(),
        company_id=uuid4(),
        requester_user_id=uuid4(),
        owner_department_type=department_type,
        active_department_type=department_type,
        request_type="foundation_test",
        request_summary="Validate deterministic department execution.",
        current_stage="department_execution_started",
    )


def test_real_department_rejects_another_active_department() -> None:
    agent = build_default_department_registry().resolve(DepartmentType.IT)
    mismatched = context(DepartmentType.HR).model_copy(
        update={"owner_department_type": DepartmentType.IT}
    )

    with pytest.raises(DepartmentContextMismatchError):
        asyncio.run(agent.execute(mismatched))
