"""Admin authorization dependencies.

Tenants:
- Company account: FULL WRITE to every area.
- Department manager: full write only for their own department domain; read other basic data.
- Employees / external users: NO admin access.
"""
from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import (
    require_authenticated_user,
    require_company_account,
)
from app.core.enums import ActorType, DepartmentType
from app.database.session import get_db_session
from app.departments.repository import DepartmentRepository


async def _resolve_department_type(
    session: AsyncSession,
    company_id: UUID,
    department_id: UUID | None,
) -> DepartmentType | None:
    if department_id is None:
        return None
    dept = await DepartmentRepository(session, company_id).get_by_id(department_id)
    return dept.department_type if dept else None


async def _department_type_from_user(
    session: AsyncSession,
    current_user: AuthenticatedUser,
) -> DepartmentType | None:
    if current_user.department_id is None:
        return None
    dept = await DepartmentRepository(
        session, current_user.company_id
    ).get_by_id(current_user.department_id)
    return dept.department_type if dept else None


def require_admin_access() -> Callable[..., AuthenticatedUser]:
    async def dependency(
        current_user: Annotated[
            AuthenticatedUser, Depends(require_authenticated_user)
        ],
    ) -> AuthenticatedUser:
        if current_user.actor_type in (
            ActorType.COMPANY,
            ActorType.DEPARTMENT_MANAGER,
        ):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return dependency


def _is_company(current_user: AuthenticatedUser) -> bool:
    return current_user.actor_type == ActorType.COMPANY


def _scoped_forbidden(detail: str = "Access denied for this resource") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Write scope helpers
# ---------------------------------------------------------------------------

DOMAIN_DEPT: dict[str, DepartmentType] = {
    "it": DepartmentType.IT,
    "finance": DepartmentType.FINANCE,
    "procurement": DepartmentType.PROCUREMENT,
    "hr": DepartmentType.HR,
    "customer_support": DepartmentType.CUSTOMER_SUPPORT,
}


async def require_company_or_department_write(
    domain: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthenticatedUser:
    """Allow writes only for company account or matching department manager."""
    if _is_company(current_user):
        return current_user
    if current_user.actor_type != ActorType.DEPARTMENT_MANAGER:
        raise _scoped_forbidden()
    expected = DOMAIN_DEPT.get(domain)
    dept_type = await _department_type_from_user(session, current_user)
    if expected is not None and dept_type == expected:
        return current_user
    raise _scoped_forbidden()


def require_company_or_department_write_dep(
    domain: str,
) -> Callable[..., AuthenticatedUser]:
    async def dependency(
        current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> AuthenticatedUser:
        return await require_company_or_department_write(domain, current_user, session)

    return dependency


# --- read-only cross-domain ---

async def require_company_or_any_manager(
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> AuthenticatedUser:
    if _is_company(current_user):
        return current_user
    if current_user.actor_type == ActorType.DEPARTMENT_MANAGER:
        return current_user
    raise _scoped_forbidden()


async def require_company_account_admin(
    current_user: Annotated[AuthenticatedUser, Depends(require_company_account)],
) -> AuthenticatedUser:
    return current_user


# Cross references for router usage
require_it_admin = require_company_or_department_write_dep("it")
require_finance_admin = require_company_or_department_write_dep("finance")
require_procurement_admin = require_company_or_department_write_dep("procurement")
require_hr_admin = require_company_or_department_write_dep("hr")
require_company_admin = require_company_account
