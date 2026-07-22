"""Onboarding API router."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    BusinessValidationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.database.session import get_db_session
from app.onboarding.dependencies import require_company_account
from app.onboarding.enums import ImportType
from app.onboarding.parser import get_template_columns, parse_upload
from app.onboarding.schemas import (
    ImportConfirmResponse,
    ImportJobListFilters,
    ImportJobResponse,
    ImportTemplateResponse,
    ImportValidateResponse,
    OnboardingActivateResponse,
    OnboardingStatusResponse,
    RowValidationResult,
    TemplateColumn,
)
from app.onboarding.service import OnboardingService
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


def _service(session: AsyncSession, current_user: AuthenticatedUser) -> OnboardingService:
    return OnboardingService(session, current_user.company_id)


def _handle_app_exceptions(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if isinstance(exc, BusinessValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if isinstance(exc, ForbiddenError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    raise exc


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> OnboardingStatusResponse:
    try:
        return await _service(session, current_user).status_service.get_status()
    except Exception as exc:
        _handle_app_exceptions(exc)


@router.post("/activate", response_model=OnboardingActivateResponse)
async def activate_company(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_company_account)],
) -> OnboardingActivateResponse:
    try:
        await _service(session, current_user).status_service.activate(current_user)
    except Exception as exc:
        _handle_app_exceptions(exc)
    return OnboardingActivateResponse(
        company_id=current_user.company_id,
        activated=True,
        message="Company activated successfully",
    )


@router.post("/imports/{import_type}/validate", response_model=ImportValidateResponse)
async def validate_import(
    import_type: ImportType,
    upload: UploadFile,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_company_account)],
) -> ImportValidateResponse:
    settings = get_settings()
    try:
        parsed = await parse_upload(upload, settings)
        return await _service(session, current_user).import_service.validate_import(
            import_type,
            parsed,
            current_user.user_id,
        )
    except Exception as exc:
        _handle_app_exceptions(exc)


@router.post("/imports/{job_id}/confirm", response_model=ImportConfirmResponse)
async def confirm_import(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_company_account)],
) -> ImportConfirmResponse:
    try:
        return await _service(session, current_user).import_service.confirm_import(
            job_id,
            current_user,
        )
    except Exception as exc:
        _handle_app_exceptions(exc)


@router.get("/imports", response_model=list[ImportJobResponse])
async def list_import_jobs(
    filters: Annotated[ImportJobListFilters, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> list[ImportJobResponse]:
    try:
        jobs = await _service(session, current_user).import_service.job_repo.list_jobs(
            import_type=filters.import_type,
            status=filters.status,
            limit=filters.limit,
            offset=filters.offset,
        )
        return [ImportJobResponse.model_validate(j) for j in jobs]
    except Exception as exc:
        _handle_app_exceptions(exc)


@router.get("/imports/{job_id}", response_model=ImportJobResponse)
async def get_import_job(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> ImportJobResponse:
    try:
        job = await _service(session, current_user).import_service.job_repo.get_by_id(
            job_id,
        )
        if job is None:
            raise NotFoundError("Import job not found")
        return ImportJobResponse.model_validate(job)
    except Exception as exc:
        _handle_app_exceptions(exc)


@router.get("/templates/{import_type}", response_model=ImportTemplateResponse)
async def get_import_template(
    import_type: ImportType,
) -> ImportTemplateResponse:
    columns = get_template_columns(import_type.value)
    return ImportTemplateResponse(
        import_type=import_type,
        columns=[TemplateColumn.model_validate(c) for c in columns],
        csv_header=",".join(c["name"] for c in columns),
    )
