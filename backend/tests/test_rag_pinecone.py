import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.core.config import Settings
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
    records = [{"_id": str(index), "chunk_text": "content"} for index in range(100)]
    asyncio.run(provider.upsert("company_test", records))
    assert provider._index.upsert_records.await_count == 2


def test_provider_normalizes_search_results() -> None:
    response = {"result": {"hits": [{"_id": "one", "_score": 0.8, "fields": {"chunk_text": "safe"}}]}}
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
    assert result == [{"_id": "one", "_score": 0.8, "chunk_text": "safe"}]
