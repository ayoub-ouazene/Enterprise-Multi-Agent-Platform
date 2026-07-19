import importlib.util
from pathlib import Path


def test_support_issue_migration_has_complete_revision_chain() -> None:
    path = Path(__file__).parents[1] / "alembic" / "versions" / "20260719_0008_support_issues.py"
    spec = importlib.util.spec_from_file_location("support_migration", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert module.revision == "20260719_0008"
    assert module.down_revision == "20260719_0007"
    assert callable(module.upgrade) and callable(module.downgrade)
