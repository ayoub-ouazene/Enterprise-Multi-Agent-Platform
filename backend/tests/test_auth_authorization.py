import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_actor_type, require_department_manager
from app.core.enums import ActorType


def context(actor_type: ActorType, *, manager: bool = False) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="user@example.com",
        actor_type=actor_type,
        employee_id=uuid4() if manager else None,
        department_id=uuid4() if manager else None,
        is_manager=manager,
    )


def test_actor_type_authorization_accepts_only_allowed_actor() -> None:
    company_only = require_actor_type(ActorType.COMPANY)

    accepted = asyncio.run(company_only(context(ActorType.COMPANY)))
    assert accepted.actor_type == ActorType.COMPANY

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(company_only(context(ActorType.EMPLOYEE)))
    assert exc_info.value.status_code == 403


def test_department_manager_requires_trusted_employee_and_department_context() -> None:
    manager = context(ActorType.DEPARTMENT_MANAGER, manager=True)
    assert asyncio.run(require_department_manager(manager)) is manager

    incomplete = context(ActorType.DEPARTMENT_MANAGER)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(require_department_manager(incomplete))
    assert exc_info.value.status_code == 403
