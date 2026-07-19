import re
from uuid import UUID


_UNSAFE_NAMESPACE_CHARACTERS = re.compile(r"[^a-zA-Z0-9_-]+")


def build_company_namespace(company_id: UUID, prefix: str) -> str:
    """Build a deterministic namespace from trusted server-side values."""
    safe_prefix = _UNSAFE_NAMESPACE_CHARACTERS.sub("_", prefix.strip()).strip("_-")
    if not safe_prefix:
        raise ValueError("PINECONE_NAMESPACE_PREFIX must contain safe characters")
    return f"{safe_prefix}_{company_id}"


def build_chunk_id(document_id: UUID, version: int, chunk_index: int) -> str:
    if version < 1 or chunk_index < 0:
        raise ValueError("Invalid chunk identity")
    return f"{document_id}:{version}:{chunk_index:04d}"
