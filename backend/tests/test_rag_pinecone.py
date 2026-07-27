import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.core.config import Settings
from app.rag.exceptions import KnowledgeProviderError
from app.rag.pinecone import PineconeProvider


def settings() -> Settings:
    return Settings(
        _env_file=None,
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        pinecone_api_key="test",
        pinecone_index_host="https://test.svc.pinecone.io",
    )


def test_provider_batches_integrated_text_upserts_without_network() -> None:
    provider = PineconeProvider(settings(), max_retries=0)
    provider._validated = True
    provider._index = SimpleNamespace(upsert_records=AsyncMock())
    records = [{"_id": str(index), "text": "content"} for index in range(100)]
    asyncio.run(provider.upsert("company_test", records))
    assert provider._index.upsert_records.await_count == 2


def test_provider_normalizes_search_results() -> None:
    response = {"result": {"hits": [{"_id": "one", "_score": 0.8, "fields": {"text": "safe"}}]}}
    provider = PineconeProvider(settings(), max_retries=0)
    provider._validated = True
    provider._index = SimpleNamespace(search=AsyncMock(return_value=response))
    result = asyncio.run(
        provider.search(
            "company_test",
            query_text="policy",
            top_k=1,
            metadata_filter={"$and": [{"is_active": {"$eq": True}}]},
        )
    )
    assert result == [{"_id": "one", "_score": 0.8, "text": "safe"}]


def test_missing_index_configuration_is_a_safe_provider_error() -> None:
    incomplete = Settings(
        _env_file=None,
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        pinecone_api_key="test",
        pinecone_index_name="test-index",
        pinecone_index_host="",
    )
    provider = PineconeProvider(incomplete, max_retries=0)

    try:
        asyncio.run(provider._ensure_index())
    except KnowledgeProviderError as exc:
        assert str(exc) == "The company knowledge service is not configured"
    else:
        raise AssertionError("Missing Pinecone configuration was accepted")
