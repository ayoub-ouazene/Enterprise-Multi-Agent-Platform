from sqlalchemy import ARRAY, Enum

from app.rag.enums import KnowledgeDepartmentScope
from app.rag.models import KnowledgeDocument
from app.rag.schemas import KnowledgeDocumentMetadata


def test_model_has_tenant_and_version_indexes() -> None:
    table = KnowledgeDocument.__table__
    assert "company_id" in table.c
    assert "supersedes_document_id" in table.c
    assert "ix_knowledge_documents_company_checksum" in {index.name for index in table.indexes}
    assert isinstance(table.c.department_scope.type, ARRAY)
    assert isinstance(table.c.department_scope.type.item_type, Enum)


def test_shared_scope_cannot_be_combined() -> None:
    try:
        KnowledgeDocumentMetadata(
            title="Policy",
            document_type="policy",
            department_scope=[KnowledgeDepartmentScope.SHARED, KnowledgeDepartmentScope.HR],
            access_scope="employees",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("ambiguous shared scope was accepted")
