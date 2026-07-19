import importlib.util
from pathlib import Path


def test_it_migration_is_complete_head_revision() -> None:
    path = Path(__file__).parents[1] / "alembic" / "versions" / "20260719_0009_it_foundation.py"
    spec = importlib.util.spec_from_file_location("it_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "20260719_0009" and module.down_revision == "20260719_0008"
    assert callable(module.upgrade) and callable(module.downgrade)
