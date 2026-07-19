import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, TypeVar

from app.core.config import Settings, validate_pinecone_configuration
from app.rag.exceptions import KnowledgeProviderError


logger = logging.getLogger(__name__)
T = TypeVar("T")
UPSERT_BATCH_SIZE = 96
DELETE_BATCH_SIZE = 1000


def _value(source: object, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


class PineconeProvider:
    """One lazy, replaceable Pinecone gateway for all knowledge operations."""

    def __init__(
        self,
        settings: Settings,
        *,
        max_retries: int = 3,
        timeout_seconds: float = 30,
    ) -> None:
        self.settings = settings
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self._client: Any = None
        self._index: Any = None
        self._validated = False
        self._lock = asyncio.Lock()

    async def _call(self, operation: str, callback: Callable[[], Awaitable[T]]) -> T:
        for attempt in range(self.max_retries + 1):
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    return await callback()
            except Exception as exc:
                if attempt >= self.max_retries:
                    logger.warning(
                        "Pinecone operation failed operation=%s retries=%s",
                        operation,
                        attempt,
                    )
                    raise KnowledgeProviderError(
                        "The company knowledge service is temporarily unavailable"
                    ) from exc
                await asyncio.sleep(min(0.25 * (2**attempt), 2.0))
        raise AssertionError("unreachable")

    async def _ensure_index(self) -> Any:
        if self._validated:
            return self._index
        async with self._lock:
            if self._validated:
                return self._index
            validate_pinecone_configuration(self.settings)
            from pinecone import PineconeAsyncio

            self._client = PineconeAsyncio(
                api_key=self.settings.pinecone_api_key.get_secret_value()
            )
            description = await self._call(
                "describe_index",
                lambda: self._client.describe_index(self.settings.pinecone_index_name),
            )
            configured_host = str(self.settings.pinecone_index_host).rstrip("/")
            actual_host = str(_value(description, "host", "")).rstrip("/")
            if actual_host and actual_host != configured_host:
                await self.close()
                raise KnowledgeProviderError("Configured Pinecone index host is incompatible")
            embed = _value(description, "embed", {}) or {}
            model = _value(embed, "model", "")
            field_map = _value(embed, "field_map", {}) or {}
            mapped_text = _value(field_map, "text", "")
            if model != self.settings.pinecone_embedding_model:
                await self.close()
                raise KnowledgeProviderError("Configured Pinecone embedding model is incompatible")
            if mapped_text != "chunk_text":
                await self.close()
                raise KnowledgeProviderError("Configured Pinecone text field is incompatible")
            self._index = self._client.IndexAsyncio(host=configured_host)
            await self._call("describe_index_stats", self._index.describe_index_stats)
            self._validated = True
            return self._index

    async def upsert(self, namespace: str, records: Sequence[dict[str, Any]]) -> None:
        index = await self._ensure_index()
        for start in range(0, len(records), UPSERT_BATCH_SIZE):
            batch = list(records[start : start + UPSERT_BATCH_SIZE])
            await self._call(
                "upsert_records",
                lambda batch=batch: index.upsert_records(namespace, batch),
            )

    async def search(
        self,
        namespace: str,
        *,
        query_text: str,
        top_k: int,
        metadata_filter: dict[str, Any],
    ) -> list[dict[str, Any]]:
        index = await self._ensure_index()
        response = await self._call(
            "search_records",
            lambda: index.search(
                namespace=namespace,
                query={
                    "inputs": {"text": query_text},
                    "top_k": top_k,
                    "filter": metadata_filter,
                },
                fields=[
                    "chunk_text",
                    "company_id",
                    "document_id",
                    "document_title",
                    "document_type",
                    "departments",
                    "access_scope",
                    "version",
                    "is_active",
                    "chunk_index",
                    "source_filename",
                    "effective_date",
                ],
            ),
        )
        result = _value(response, "result", response)
        hits = _value(result, "hits", []) or []
        normalized: list[dict[str, Any]] = []
        for hit in hits:
            fields = _value(hit, "fields", {}) or {}
            normalized.append(
                {
                    "_id": _value(hit, "_id", _value(hit, "id", "")),
                    "_score": _value(hit, "_score", _value(hit, "score", 0.0)),
                    **dict(fields),
                }
            )
        return normalized

    async def fetch(self, namespace: str, ids: Sequence[str]) -> set[str]:
        index = await self._ensure_index()
        found: set[str] = set()
        for start in range(0, len(ids), DELETE_BATCH_SIZE):
            batch = list(ids[start : start + DELETE_BATCH_SIZE])
            response = await self._call(
                "fetch_records", lambda batch=batch: index.fetch(ids=batch, namespace=namespace)
            )
            vectors = _value(response, "vectors", {}) or {}
            found.update(str(item) for item in vectors)
        return found

    async def delete(self, namespace: str, ids: Sequence[str]) -> None:
        index = await self._ensure_index()
        for start in range(0, len(ids), DELETE_BATCH_SIZE):
            batch = list(ids[start : start + DELETE_BATCH_SIZE])
            await self._call(
                "delete_records",
                lambda batch=batch: index.delete(ids=batch, namespace=namespace),
            )

    async def close(self) -> None:
        index, client = self._index, self._client
        self._index = None
        self._client = None
        self._validated = False
        if index is not None and hasattr(index, "close"):
            result = index.close()
            if result is not None:
                await result
        if client is not None and hasattr(client, "close"):
            result = client.close()
            if result is not None:
                await result
