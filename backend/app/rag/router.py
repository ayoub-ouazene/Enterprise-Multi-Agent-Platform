import json
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_request_settings, require_actor_type
from app.core.config import Settings
from app.core.enums import ActorType
from app.database.session import get_db_session
from app.rag.dependencies import get_pinecone_provider
from app.rag.exceptions import (
    KnowledgeConflictError,
    KnowledgeExtractionError,
    KnowledgeNotFoundError,
    KnowledgePermissionError,
    KnowledgeProviderError,
    KnowledgeValidationError,
)
from app.rag.ingestion import KnowledgeIngestionService
from app.rag.pinecone import PineconeProvider
from app.rag.retrieval import KnowledgeRetrievalService
from app.rag.schemas import (
    KnowledgeChunkResult,
    KnowledgeDocumentListFilters,
    KnowledgeDocumentMetadata,
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
)


router = APIRouter(prefix="/api/v1/documents", tags=["knowledge-documents"])
require_knowledge_manager = require_actor_type(
    ActorType.COMPANY, ActorType.DEPARTMENT_MANAGER
)


def _metadata(
    *,
    title: str,
    document_type: str,
    department_scope: list[str],
    access_scope: str,
    effective_date: date | None,
    custom_metadata: str,
) -> KnowledgeDocumentMetadata:
    try:
        parsed_metadata = json.loads(custom_metadata or "{}")
        return KnowledgeDocumentMetadata(
            title=title,
            document_type=document_type,
            department_scope=department_scope,
            access_scope=access_scope,
            effective_date=effective_date,
            custom_metadata=parsed_metadata,
        )
    except (json.JSONDecodeError, ValidationError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid document metadata",
        ) from None


def _raise_http(exc: Exception) -> None:
    if isinstance(exc, KnowledgePermissionError):
        code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, KnowledgeNotFoundError):
        code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, KnowledgeConflictError):
        code = status.HTTP_409_CONFLICT
    elif isinstance(exc, KnowledgeProviderError):
        code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, (KnowledgeValidationError, KnowledgeExtractionError)):
        code = status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        raise exc
    raise HTTPException(status_code=code, detail=str(exc)) from None


def _ingestion_service(
    session: AsyncSession,
    current_user: AuthenticatedUser,
    settings: Settings,
    provider: PineconeProvider,
) -> KnowledgeIngestionService:
    return KnowledgeIngestionService(session, current_user, settings, provider)


@router.post("", response_model=KnowledgeDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    document_type: Annotated[str, Form()],
    department_scope: Annotated[list[str], Form()],
    access_scope: Annotated[str, Form()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_knowledge_manager)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    provider: Annotated[PineconeProvider, Depends(get_pinecone_provider)],
    effective_date: Annotated[date | None, Form()] = None,
    custom_metadata: Annotated[str, Form()] = "{}",
) -> KnowledgeDocumentResponse:
    metadata = _metadata(
        title=title,
        document_type=document_type,
        department_scope=department_scope,
        access_scope=access_scope,
        effective_date=effective_date,
        custom_metadata=custom_metadata,
    )
    try:
        document = await _ingestion_service(
            session, current_user, settings, provider
        ).create(file, metadata)
        return KnowledgeDocumentResponse.model_validate(document)
    except Exception as exc:
        _raise_http(exc)


@router.get("", response_model=list[KnowledgeDocumentResponse])
async def list_documents(
    filters: Annotated[KnowledgeDocumentListFilters, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_knowledge_manager)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    provider: Annotated[PineconeProvider, Depends(get_pinecone_provider)],
) -> list[KnowledgeDocumentResponse]:
    try:
        documents = await _ingestion_service(
            session, current_user, settings, provider
        ).list(filters)
        return [KnowledgeDocumentResponse.model_validate(item) for item in documents]
    except Exception as exc:
        _raise_http(exc)


@router.post("/search", response_model=list[KnowledgeChunkResult])
async def search_documents(
    payload: KnowledgeSearchRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_knowledge_manager)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    provider: Annotated[PineconeProvider, Depends(get_pinecone_provider)],
) -> list[KnowledgeChunkResult]:
    try:
        return await KnowledgeRetrievalService(
            session, current_user, settings, provider
        ).search(payload)
    except Exception as exc:
        _raise_http(exc)


@router.get("/{document_id}", response_model=KnowledgeDocumentResponse)
async def get_document(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_knowledge_manager)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    provider: Annotated[PineconeProvider, Depends(get_pinecone_provider)],
) -> KnowledgeDocumentResponse:
    try:
        document = await _ingestion_service(
            session, current_user, settings, provider
        ).get(document_id)
        return KnowledgeDocumentResponse.model_validate(document)
    except Exception as exc:
        _raise_http(exc)


@router.post("/{document_id}/replace", response_model=KnowledgeDocumentResponse)
async def replace_document(
    document_id: UUID,
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    document_type: Annotated[str, Form()],
    department_scope: Annotated[list[str], Form()],
    access_scope: Annotated[str, Form()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_knowledge_manager)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    provider: Annotated[PineconeProvider, Depends(get_pinecone_provider)],
    effective_date: Annotated[date | None, Form()] = None,
    custom_metadata: Annotated[str, Form()] = "{}",
) -> KnowledgeDocumentResponse:
    metadata = _metadata(
        title=title,
        document_type=document_type,
        department_scope=department_scope,
        access_scope=access_scope,
        effective_date=effective_date,
        custom_metadata=custom_metadata,
    )
    try:
        document = await _ingestion_service(
            session, current_user, settings, provider
        ).replace(document_id, file, metadata)
        return KnowledgeDocumentResponse.model_validate(document)
    except Exception as exc:
        _raise_http(exc)


@router.post("/{document_id}/retry-ingestion", response_model=KnowledgeDocumentResponse)
async def retry_document_ingestion(
    document_id: UUID,
    file: Annotated[UploadFile, File()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_knowledge_manager)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    provider: Annotated[PineconeProvider, Depends(get_pinecone_provider)],
) -> KnowledgeDocumentResponse:
    try:
        document = await _ingestion_service(
            session, current_user, settings, provider
        ).retry(document_id, file)
        return KnowledgeDocumentResponse.model_validate(document)
    except Exception as exc:
        _raise_http(exc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_knowledge_manager)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    provider: Annotated[PineconeProvider, Depends(get_pinecone_provider)],
) -> Response:
    try:
        await _ingestion_service(session, current_user, settings, provider).delete(
            document_id
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _raise_http(exc)
