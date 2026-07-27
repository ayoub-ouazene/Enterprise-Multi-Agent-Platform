"""Onboarding-specific dependency helpers."""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_setup_authenticated_user
from app.core.enums import ActorType
from app.database.session import get_db_session


async def require_company_account(
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_setup_authenticated_user),
    ],
) -> AuthenticatedUser:
    if current_user.actor_type != ActorType.COMPANY:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Company accounts can access onboarding",
        )
    return current_user
