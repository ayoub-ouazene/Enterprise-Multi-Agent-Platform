import asyncio
import subprocess
import sys
from unittest.mock import AsyncMock, Mock

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.health import check_database_health
from app.database.url import normalize_asyncpg_url


def test_application_and_bootstrap_entrypoints_register_all_models() -> None:
    for module_name in ("app.main", "app.auth.bootstrap"):
        code = (
            f"import {module_name}; "
            "from sqlalchemy.orm import configure_mappers; "
            "configure_mappers()"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr


def test_database_health_check_executes_select_one() -> None:
    session = AsyncMock(spec=AsyncSession)
    result = Mock()
    result.scalar_one.return_value = 1
    session.execute.return_value = result

    healthy = asyncio.run(check_database_health(session))

    assert healthy is True
    session.execute.assert_awaited_once()
    statement = session.execute.await_args.args[0]
    assert str(statement) == "SELECT 1"


def test_database_health_check_handles_sqlalchemy_failure() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.execute.side_effect = SQLAlchemyError("database unavailable")

    healthy = asyncio.run(check_database_health(session))

    assert healthy is False


def test_asyncpg_url_normalization_preserves_ssl_requirement() -> None:
    url = normalize_asyncpg_url(
        "postgresql+asyncpg://user:fake-password@localhost/test?sslmode=require"
    )

    assert "sslmode" not in url.query
    assert url.query["ssl"] == "require"
