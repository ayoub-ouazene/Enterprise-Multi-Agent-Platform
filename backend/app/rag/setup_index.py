import argparse
import asyncio
from typing import Any, Mapping

from app.core.config import get_settings, validate_pinecone_configuration


def _value(source: object, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _validate_description(
    description: object, model: str, configured_host: str | None = None
) -> str:
    host = str(_value(description, "host", ""))
    embed = _value(description, "embed", {}) or {}
    actual_model = _value(embed, "model", "")
    field_map = _value(embed, "field_map", {}) or {}
    text_field = _value(field_map, "text", "")
    if actual_model != model:
        raise RuntimeError("Existing index uses an incompatible embedding model")
    if text_field != "chunk_text":
        raise RuntimeError("Existing index uses an incompatible embedding field map")
    if configured_host and host.rstrip("/") != configured_host.rstrip("/"):
        raise RuntimeError("Configured index host does not match the existing index")
    return host


async def run(command: str, cloud: str | None, region: str | None) -> None:
    settings = get_settings()
    if settings.pinecone_api_key is None:
        raise RuntimeError("PINECONE_API_KEY must be configured")
    from pinecone import PineconeAsyncio

    async with PineconeAsyncio(
        api_key=settings.pinecone_api_key.get_secret_value()
    ) as client:
        exists = await client.has_index(settings.pinecone_index_name)
        created = False
        if not exists:
            if command != "create":
                raise RuntimeError("Configured Pinecone index does not exist")
            if not cloud or not region:
                raise RuntimeError("--cloud and --region are required for index creation")
            await client.create_index_for_model(
                name=settings.pinecone_index_name,
                cloud=cloud,
                region=region,
                embed={
                    "model": settings.pinecone_embedding_model,
                    "field_map": {"text": "chunk_text"},
                    "read_parameters": {"input_type": "query", "truncate": "NONE"},
                    "write_parameters": {"input_type": "passage", "truncate": "NONE"},
                },
            )
            created = True
        description = await client.describe_index(settings.pinecone_index_name)
        ready = _value(_value(description, "status", {}) or {}, "ready", None)
        if ready is False and created:
            for _ in range(30):
                await asyncio.sleep(2)
                description = await client.describe_index(settings.pinecone_index_name)
                ready = _value(
                    _value(description, "status", {}) or {}, "ready", None
                )
                if ready is not False:
                    break
        if ready is False:
            raise RuntimeError("Configured Pinecone index is not ready")
        host = _validate_description(
            description,
            settings.pinecone_embedding_model,
            str(settings.pinecone_index_host) if settings.pinecone_index_host else None,
        )
        if not host:
            raise RuntimeError("Pinecone did not report an index host")
        print(f"Pinecone index is compatible. PINECONE_INDEX_HOST={host}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate or create the RAG index")
    parser.add_argument("command", choices=("check", "create"))
    parser.add_argument("--cloud")
    parser.add_argument("--region")
    args = parser.parse_args()
    asyncio.run(run(args.command, args.cloud, args.region))


if __name__ == "__main__":
    main()
