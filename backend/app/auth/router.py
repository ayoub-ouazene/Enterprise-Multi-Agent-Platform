from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import (
    get_request_settings,
    require_setup_authenticated_user,
)
from app.auth.schemas import (
    AuthenticatedUserResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.auth.service import (
    AuthenticationError,
    AuthenticationService,
    CompanyInactiveError,
    InactiveUserError,
    TokenPair,
    WorkspaceNotFoundError,
)
from app.core.config import Settings
from app.database.session import get_db_session


router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def _authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _raise_login_error(exc: AuthenticationError) -> None:
    if isinstance(exc, WorkspaceNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company workspace was not found",
        ) from None
    if isinstance(exc, InactiveUserError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        ) from None
    if isinstance(exc, CompanyInactiveError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company workspace is not active",
        ) from None
    raise _authentication_error() from None


def _token_response(pair: TokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        access_token_expires_in=pair.access_token_expires_in,
        refresh_token_expires_in=pair.refresh_token_expires_in,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> TokenResponse:
    try:
        pair = await AuthenticationService(session, settings).login(
            payload.company_slug,
            str(payload.email),
            payload.password.get_secret_value(),
        )
    except AuthenticationError as exc:
        _raise_login_error(exc)
    return _token_response(pair)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> TokenResponse:
    try:
        pair = await AuthenticationService(session, settings).refresh(
            payload.refresh_token.get_secret_value()
        )
    except AuthenticationError:
        raise _authentication_error() from None
    return _token_response(pair)


@router.get("/me", response_model=AuthenticatedUserResponse)
async def me(
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_setup_authenticated_user),
    ],
) -> AuthenticatedUserResponse:
    return AuthenticatedUserResponse.from_context(current_user)


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_setup_authenticated_user),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> ChangePasswordResponse:
    try:
        await AuthenticationService(session, settings).change_password(
            user_id=current_user.user_id,
            company_id=current_user.company_id,
            current_password=payload.current_password.get_secret_value(),
            new_password=payload.new_password.get_secret_value(),
        )
    except AuthenticationError:
        raise _authentication_error() from None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ChangePasswordResponse()
