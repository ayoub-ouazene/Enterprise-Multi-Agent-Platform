import pytest

from app.rag.chunking import chunk_text
from app.rag.exceptions import KnowledgeValidationError
from app.rag.extractors import clean_text


def test_text_cleaning_preserves_paragraphs() -> None:
    assert clean_text("Heading\r\n\r\n  Rule   one.\x00\n\n\nRule two.") == (
        "Heading\n\nRule one.\n\nRule two."
    )


def test_chunks_are_ordered_bounded_and_overlap() -> None:
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    chunks = chunk_text(
        text, chunk_size=28, overlap=6, embedding_model="multilingual-e5-large"
    )
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.text and len(chunk.text) <= 28 for chunk in chunks)
    assert len(chunks) > 1


def test_unicode_chunks_respect_embedding_byte_limit() -> None:
    chunks = chunk_text(
        "é" * 400,
        chunk_size=400,
        overlap=60,
        embedding_model="multilingual-e5-large",
    )
    assert all(len(chunk.text.encode("utf-8")) <= 480 for chunk in chunks)


def test_empty_text_and_invalid_overlap_are_rejected() -> None:
    with pytest.raises(KnowledgeValidationError):
        chunk_text(" ", chunk_size=10, overlap=1, embedding_model="x")
    with pytest.raises(KnowledgeValidationError):
        chunk_text("content", chunk_size=10, overlap=10, embedding_model="x")
