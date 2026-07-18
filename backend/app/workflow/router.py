from typing import Annotated, Awaitable, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.auth.dependencies import get_request_settings
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.database.session import get_db_session
from app.workflow.exceptions import (
    WorkflowConflictError,
    WorkflowExecutionFailedError,
    WorkflowPermissionError,
    WorkflowPersistenceError,
)
from app.workflow.schemas import WorkflowControlResponse
from app.workflow.service import WorkflowService
from app.llm.exceptions import (
    RouterConfigurationError,
    RouterOutputError,
    RouterProviderError,
)


router = APIRouter(prefix="/api/v1/requests", tags=["workflow"])


def _service(
    session: AsyncSession,
    current_user: AuthenticatedUser,
    settings: Settings,
) -> WorkflowService:
    return WorkflowService(session, current_user, settings=settings)


async def _control_workflow(
    operation: Callable[[UUID], Awaitable[WorkflowControlResponse]],
    request_id: UUID,
) -> WorkflowControlResponse:
    try:
        return await operation(request_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business request not found",
        ) from None
    except WorkflowPermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        ) from None
    except WorkflowConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from None
    except WorkflowPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow persistence is unavailable",
        ) from None
    except WorkflowExecutionFailedError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow execution failed",
        ) from None
    except RouterConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The Router is not configured",
        ) from None
    except (RouterProviderError, RouterOutputError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The Router is temporarily unavailable",
        ) from None


@router.post(
    "/{request_id}/workflow/start",
    response_model=WorkflowControlResponse,
)
async def start_workflow(
    request_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> WorkflowControlResponse:
    service = _service(session, current_user, settings)
    return await _control_workflow(service.start, request_id)


@router.post(
    "/{request_id}/workflow/resume",
    response_model=WorkflowControlResponse,
)
async def resume_workflow(
    request_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> WorkflowControlResponse:
    service = _service(session, current_user, settings)
    return await _control_workflow(service.resume, request_id)
