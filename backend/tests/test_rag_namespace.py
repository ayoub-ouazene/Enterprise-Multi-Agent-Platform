from uuid import uuid4

import pytest

from app.rag.namespace import build_chunk_id, build_company_namespace


def test_company_namespace_is_deterministic_and_sanitized() -> None:
    company_id = uuid4()
    assert build_company_namespace(company_id, "company") == f"company_{company_id}"
    assert build_company_namespace(company_id, "tenant space!") == f"tenant_space_{company_id}"


def test_different_companies_have_different_namespaces() -> None:
    assert build_company_namespace(uuid4(), "company") != build_company_namespace(
        uuid4(), "company"
    )


def test_empty_namespace_prefix_is_rejected() -> None:
    with pytest.raises(ValueError):
        build_company_namespace(uuid4(), "!!!")


def test_chunk_identity_is_deterministic() -> None:
    document_id = uuid4()
    assert build_chunk_id(document_id, 2, 7) == f"{document_id}:2:0007"
