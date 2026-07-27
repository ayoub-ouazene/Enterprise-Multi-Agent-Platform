from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_request_settings
from app.auth.router import _token_response
from app.auth.schemas import TokenResponse
from app.companies.schemas import CompanyRegistrationRequest
from app.companies.service import CompanyService
from app.core.config import Settings
from app.core.exceptions import ConflictError
from app.database.session import get_db_session


router = APIRouter(prefix="/api/v1/companies", tags=["companies"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_company(
    payload: CompanyRegistrationRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> TokenResponse:
    try:
        tokens = await CompanyService(session).register(payload, settings)
    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company workspace already exists",
        ) from exc
    return _token_response(tokens)
