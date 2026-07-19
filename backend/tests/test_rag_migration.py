from pathlib import Path


def test_knowledge_migration_has_complete_upgrade_and_downgrade() -> None:
    path = Path(__file__).parents[1] / "alembic" / "versions" / "20260719_0007_knowledge_documents.py"
    source = path.read_text(encoding="utf-8")
    assert 'revision: str = "20260719_0007"' in source
    assert 'down_revision: str | Sequence[str] | None = "20260718_0006"' in source
    assert 'op.create_table(\n        "knowledge_documents"' in source
    assert 'op.drop_table("knowledge_documents")' in source
    assert "knowledge_department_scope" in source
