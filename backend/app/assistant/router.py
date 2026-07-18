from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.schemas import AssistantMessageRequest, AssistantMessageResponse
from app.assistant.service import AssistantService
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import (
    get_request_settings,
    require_authenticated_user,
)
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.database.session import get_db_session
from app.llm.exceptions import (
    RouterConfigurationError,
    RouterOutputError,
    RouterProviderError,
)
from app.workflow.exceptions import (
    WorkflowConflictError,
    WorkflowExecutionFailedError,
    WorkflowPermissionError,
    WorkflowPersistenceError,
)


router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


def _service(
    session: AsyncSession,
    current_user: AuthenticatedUser,
    settings: Settings,
) -> AssistantService:
    return AssistantService(session, current_user, settings)


@router.post("/message", response_model=AssistantMessageResponse)
async def assistant_message(
    payload: AssistantMessageRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> AssistantMessageResponse:
    try:
        return await _service(session, current_user, settings).handle(payload)
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
    except RouterConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The Platform Assistant is not configured",
        ) from None
    except (RouterProviderError, RouterOutputError, WorkflowExecutionFailedError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The Platform Assistant is temporarily unavailable",
        ) from None
    except WorkflowPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow persistence is unavailable",
        ) from None
