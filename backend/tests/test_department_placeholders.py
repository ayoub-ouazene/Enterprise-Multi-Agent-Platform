import asyncio
from uuid import uuid4

import pytest

from app.core.enums import DepartmentType
from app.departments.contracts import (
    DepartmentExecutionContext,
    DepartmentExecutionResult,
)
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


@pytest.mark.parametrize(
    "department_type",
        [item for item in DepartmentType if item not in {
            DepartmentType.CUSTOMER_SUPPORT, DepartmentType.IT}],
)
def test_each_placeholder_returns_strict_deterministic_completion(
    department_type: DepartmentType,
) -> None:
    agent = build_default_department_registry().resolve(department_type)

    first = asyncio.run(agent.execute(context(department_type)))
    second = asyncio.run(agent.execute(context(department_type)))

    assert isinstance(first, DepartmentExecutionResult)
    assert first.department_type == department_type
    assert first.next_action.value == "complete_request"
    assert first.status.value == "completed"
    assert first.is_terminal is True
    assert first.completed_step == f"{department_type.value}_placeholder_completed"
    assert first.model_dump(exclude={"state_updates"}) == second.model_dump(
        exclude={"state_updates"}
    )


def test_placeholder_rejects_another_active_department() -> None:
    agent = build_default_department_registry().resolve(DepartmentType.IT)
    mismatched = context(DepartmentType.HR).model_copy(
        update={"owner_department_type": DepartmentType.IT}
    )

    with pytest.raises(DepartmentContextMismatchError):
        asyncio.run(agent.execute(mismatched))
