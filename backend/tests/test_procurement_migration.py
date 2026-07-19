from pathlib import Path


MIGRATION = Path("alembic/versions/20260719_0011_procurement_foundation.py")


def test_procurement_migration_has_linear_revision_and_complete_tables() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "20260719_0011"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260719_0010"' in text
    assert '"procurement_requests"' in text
    assert '"supplier_candidates"' in text
    assert "fk_procurement_requests_selected_candidate" in text
    assert "uq_supplier_candidates_one_selected" in text
    assert 'op.drop_table("supplier_candidates")' in text
    assert 'op.drop_table("procurement_requests")' in text
