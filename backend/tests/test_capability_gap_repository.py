import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.failures.enums import CapabilityGapStatus
from app.failures.repository import CapabilityGapRepository


def call(repository, key="key"):
    return asyncio.run(
        repository.create_or_increment(
            request_id=None,
            department_id=None,
            requested_operation="Export records",
            normalized_operation="export_records",
            deduplication_key=key,
            description="Unsupported",
            safe_user_message="Not supported",
            metadata={},
            now=datetime.now(UTC),
        )
    )


def test_new_capability_gap_is_created_without_commit() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    repository = CapabilityGapRepository(session, uuid4())
    gap, created = call(repository)
    assert created is True
    assert gap.occurrence_count == 1
    assert gap.status == CapabilityGapStatus.OPEN
    session.commit.assert_not_awaited()


def test_matching_unresolved_gap_increments_occurrence() -> None:
    existing = SimpleNamespace(occurrence_count=2, last_seen_at=None, request_id=None)
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = existing
    repository = CapabilityGapRepository(session, uuid4())
    gap, created = call(repository)
    assert created is False
    assert gap.occurrence_count == 3


def test_unrelated_keys_create_separate_gap_candidates() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    repository = CapabilityGapRepository(session, uuid4())
    first, _ = call(repository, "one")
    second, _ = call(repository, "two")
    assert first.deduplication_key != second.deduplication_key
