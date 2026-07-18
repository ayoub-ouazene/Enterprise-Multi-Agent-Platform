from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.service import AuthenticationError, AuthenticationService
from app.core.config import Settings
from app.core.enums import ActorType
from app.database.session import get_db_session


bearer_scheme = HTTPBearer(auto_error=False)


def get_request_settings(request: Request) -> Settings:
    settings: Settings | None = getattr(request.app.state, "settings", None)
    if settings is None:
        raise RuntimeError("Application settings are not initialized")
    return settings


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    try:
        return await AuthenticationService(session, settings).authenticate_access_token(
            credentials.credentials
        )
    except AuthenticationError:
        raise _unauthorized() from None


async def require_authenticated_user(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    return current_user


def require_actor_type(
    *allowed_actor_types: ActorType,
) -> Callable[..., AuthenticatedUser]:
    allowed = frozenset(allowed_actor_types)

    async def dependency(
        current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    ) -> AuthenticatedUser:
        if current_user.actor_type not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return dependency


async def require_company_account(
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_actor_type(ActorType.COMPANY)),
    ],
) -> AuthenticatedUser:
    return current_user


async def require_department_manager(
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_actor_type(ActorType.DEPARTMENT_MANAGER)),
    ],
) -> AuthenticatedUser:
    if (
        not current_user.is_manager
        or current_user.employee_id is None
        or current_user.department_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Department manager context is required",
        )
    return current_user
