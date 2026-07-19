import re

from app.rag.exceptions import KnowledgeValidationError
from app.rag.schemas import TextChunk


MAX_CHUNKS_PER_DOCUMENT = 10_000
MULTILINGUAL_E5_SAFE_UTF8_BYTES = 480
_BOUNDARY = re.compile(r"(?:\n\n|(?<=[.!?])\s+)")


def _bounded_end(text: str, start: int, desired_end: int, byte_limit: int) -> int:
    end = min(desired_end, len(text))
    while end > start and len(text[start:end].encode("utf-8")) > byte_limit:
        end -= 1
    if end == start:
        raise KnowledgeValidationError("Document contains text that cannot be safely chunked")
    return end


def chunk_text(
    text: str,
    *,
    chunk_size: int,
    overlap: int,
    embedding_model: str,
) -> list[TextChunk]:
    if not text.strip():
        raise KnowledgeValidationError("Document contains no usable text")
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise KnowledgeValidationError("Invalid RAG chunk size or overlap")

    byte_limit = (
        MULTILINGUAL_E5_SAFE_UTF8_BYTES
        if embedding_model == "multilingual-e5-large"
        else chunk_size * 4
    )
    chunks: list[TextChunk] = []
    start = 0
    while start < len(text):
        hard_end = _bounded_end(text, start, start + chunk_size, byte_limit)
        end = hard_end
        if hard_end < len(text):
            candidates = [match.end() for match in _BOUNDARY.finditer(text, start, hard_end)]
            minimum = start + max(1, (hard_end - start) // 2)
            useful = [candidate for candidate in candidates if candidate >= minimum]
            if useful:
                end = useful[-1]
        value = text[start:end].strip()
        if value:
            chunks.append(TextChunk(index=len(chunks), text=value))
        if len(chunks) > MAX_CHUNKS_PER_DOCUMENT:
            raise KnowledgeValidationError("Document produces too many knowledge chunks")
        if end >= len(text):
            break
        next_start = max(start + 1, end - overlap)
        while next_start < end and text[next_start].isspace():
            next_start += 1
        start = next_start
    if not chunks:
        raise KnowledgeValidationError("Document contains no usable text chunks")
    return chunks
