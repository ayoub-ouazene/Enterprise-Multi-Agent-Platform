import importlib.util
from pathlib import Path


def test_finance_migration_has_complete_revision_and_tables() -> None:
    path = Path(__file__).parents[1] / "alembic/versions/20260719_0010_finance_foundation.py"
    spec = importlib.util.spec_from_file_location("finance_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "20260719_0010"
    assert module.down_revision == "20260719_0009"
    source = path.read_text(encoding="utf-8")
    for table in ("budgets", "finance_requests", "financial_transactions"):
        assert f'"{table}"' in source
    assert "with_for_update" not in source
    assert "def downgrade" in source
