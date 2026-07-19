from typing import Annotated

from fastapi import Depends, Request

from app.auth.dependencies import get_request_settings
from app.core.config import Settings
from app.rag.pinecone import PineconeProvider


def get_pinecone_provider(
    request: Request,
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> PineconeProvider:
    provider = getattr(request.app.state, "pinecone_provider", None)
    if provider is None:
        provider = PineconeProvider(settings)
        request.app.state.pinecone_provider = provider
    return provider
