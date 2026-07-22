"""Onboarding-specific dependency helpers."""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_actor_type
from app.core.enums import ActorType
from app.database.session import get_db_session


async def require_company_account(
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_actor_type(ActorType.COMPANY)),
    ],
) -> AuthenticatedUser:
    return current_user
