from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import _unauthorized
from app.auth.service import AuthenticationError, AuthenticationService
from app.core.config import Settings
from app.database.session import AsyncSessionFactory

bearer_scheme = HTTPBearer(auto_error=False)


async def _authenticate_token(
    session: AsyncSession,
    settings: Settings,
    raw_token: str,
) -> AuthenticatedUser:
    try:
        return await AuthenticationService(session, settings).authenticate_access_token(
            raw_token
        )
    except AuthenticationError:
        raise _unauthorized() from None


async def get_current_user_for_sse(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    token: Annotated[str | None, Query()] = None,
) -> AuthenticatedUser:
    """Authenticate SSE requests via Authorization header or ?token= query param.

    Opens a short-lived database session for token validation only.
    """
    settings: Settings | None = getattr(request.app.state, "settings", None)
    if settings is None:
        raise RuntimeError("Application settings are not initialized")

    session_factory: AsyncSessionFactory | None = getattr(
        request.app.state,
        "session_factory",
        None,
    )
    if session_factory is None:
        raise RuntimeError("Database session factory is not initialized")

    raw_token: str | None = None
    if credentials is not None and credentials.scheme.lower() == "bearer":
        raw_token = credentials.credentials
    elif token is not None and token.strip():
        raw_token = token.strip()

    if raw_token is None:
        raise _unauthorized()

    async with session_factory() as session:
        return await _authenticate_token(session, settings, raw_token)
