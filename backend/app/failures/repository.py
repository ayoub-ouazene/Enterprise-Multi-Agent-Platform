from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.departments.models import Department
from app.failures.enums import (
    CapabilityGapStatus,
    FailureSource,
    FailureType,
    UNRESOLVED_GAP_STATUSES,
)
from app.failures.models import CapabilityGap, FailureLog
from app.requests.models import BusinessRequest


class FailureLogRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def _references_valid(
        self, request_id: UUID | None, department_id: UUID | None
    ) -> bool:
        if (
            request_id is not None
            and await self.session.scalar(
                select(BusinessRequest.id).where(
                    BusinessRequest.id == request_id,
                    BusinessRequest.company_id == self.company_id,
                )
            )
            is None
        ):
            return False
        if (
            department_id is not None
            and await self.session.scalar(
                select(Department.id).where(
                    Department.id == department_id,
                    Department.company_id == self.company_id,
                )
            )
            is None
        ):
            return False
        return True

    async def create(
        self,
        *,
        request_id: UUID | None,
        department_id: UUID | None,
        failure_type: FailureType,
        failure_source: FailureSource,
        failed_operation: str,
        internal_message: str,
        safe_message: str,
        error_code: str | None,
        technical_data: dict[str, object],
        alternative_attempted: bool,
        alternative_description: str | None,
        is_terminal: bool,
    ) -> FailureLog | None:
        if not await self._references_valid(request_id, department_id):
            return None
        failure = FailureLog(
            company_id=self.company_id,
            request_id=request_id,
            department_id=department_id,
            failure_type=failure_type,
            failure_source=failure_source,
            failed_operation=failed_operation,
            internal_message=internal_message,
            safe_message=safe_message,
            error_code=error_code,
            technical_data=technical_data,
            alternative_attempted=alternative_attempted,
            alternative_description=alternative_description,
            is_terminal=is_terminal,
            resolved=False,
        )
        self.session.add(failure)
        await self.session.flush()
        return failure

    async def get_by_id(
        self, failure_id: UUID, *, department_id: UUID | None = None
    ) -> FailureLog | None:
        statement = select(FailureLog).where(
            FailureLog.id == failure_id, FailureLog.company_id == self.company_id
        )
        if department_id is not None:
            statement = statement.where(FailureLog.department_id == department_id)
        return await self.session.scalar(statement)

    async def list(
        self,
        *,
        department_id: UUID | None = None,
        failure_type: FailureType | None = None,
        failure_source: FailureSource | None = None,
        resolved: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FailureLog]:
        statement = select(FailureLog).where(FailureLog.company_id == self.company_id)
        if department_id is not None:
            statement = statement.where(FailureLog.department_id == department_id)
        if failure_type is not None:
            statement = statement.where(FailureLog.failure_type == failure_type)
        if failure_source is not None:
            statement = statement.where(FailureLog.failure_source == failure_source)
        if resolved is not None:
            statement = statement.where(FailureLog.resolved == resolved)
        result = await self.session.scalars(
            statement.order_by(FailureLog.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.all())

    async def resolve(
        self, failure_id: UUID, *, resolved_at: datetime, resolved_by_user_id: UUID
    ) -> FailureLog | None:
        return await self.session.scalar(
            update(FailureLog)
            .where(
                FailureLog.id == failure_id,
                FailureLog.company_id == self.company_id,
                FailureLog.resolved.is_(False),
            )
            .values(
                resolved=True,
                resolved_at=resolved_at,
                resolved_by_user_id=resolved_by_user_id,
            )
            .returning(FailureLog)
        )


class CapabilityGapRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def _references_valid(
        self, request_id: UUID | None, department_id: UUID | None
    ) -> bool:
        if (
            request_id is not None
            and await self.session.scalar(
                select(BusinessRequest.id).where(
                    BusinessRequest.id == request_id,
                    BusinessRequest.company_id == self.company_id,
                )
            )
            is None
        ):
            return False
        if (
            department_id is not None
            and await self.session.scalar(
                select(Department.id).where(
                    Department.id == department_id,
                    Department.company_id == self.company_id,
                )
            )
            is None
        ):
            return False
        return True

    async def create_or_increment(
        self,
        *,
        request_id: UUID | None,
        department_id: UUID | None,
        requested_operation: str,
        normalized_operation: str,
        deduplication_key: str,
        description: str,
        safe_user_message: str,
        metadata: dict[str, object],
        now: datetime,
    ) -> tuple[CapabilityGap, bool] | None:
        if not await self._references_valid(request_id, department_id):
            return None
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"{self.company_id}:{deduplication_key}"},
        )
        gap = await self.session.scalar(
            select(CapabilityGap)
            .where(
                CapabilityGap.company_id == self.company_id,
                CapabilityGap.deduplication_key == deduplication_key,
                CapabilityGap.status.in_(UNRESOLVED_GAP_STATUSES),
            )
            .with_for_update()
        )
        if gap is not None:
            gap.occurrence_count += 1
            gap.last_seen_at = now
            if request_id is not None:
                gap.request_id = request_id
            await self.session.flush()
            return gap, False
        gap = CapabilityGap(
            company_id=self.company_id,
            request_id=request_id,
            department_id=department_id,
            requested_operation=requested_operation,
            normalized_operation=normalized_operation,
            deduplication_key=deduplication_key,
            description=description,
            safe_user_message=safe_user_message,
            status=CapabilityGapStatus.OPEN,
            occurrence_count=1,
            first_seen_at=now,
            last_seen_at=now,
            gap_metadata=metadata,
        )
        self.session.add(gap)
        await self.session.flush()
        return gap, True

    async def get_by_id(
        self, gap_id: UUID, *, department_id: UUID | None = None
    ) -> CapabilityGap | None:
        statement = select(CapabilityGap).where(
            CapabilityGap.id == gap_id, CapabilityGap.company_id == self.company_id
        )
        if department_id is not None:
            statement = statement.where(CapabilityGap.department_id == department_id)
        return await self.session.scalar(statement)

    async def list(
        self,
        *,
        department_id: UUID | None = None,
        status: CapabilityGapStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CapabilityGap]:
        statement = select(CapabilityGap).where(
            CapabilityGap.company_id == self.company_id
        )
        if department_id is not None:
            statement = statement.where(CapabilityGap.department_id == department_id)
        if status is not None:
            statement = statement.where(CapabilityGap.status == status)
        result = await self.session.scalars(
            statement.order_by(CapabilityGap.last_seen_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())

    async def update_status(
        self,
        gap_id: UUID,
        *,
        status: CapabilityGapStatus,
        resolution_notes: str | None,
        resolved_at: datetime | None,
        resolved_by_user_id: UUID | None,
    ) -> CapabilityGap | None:
        return await self.session.scalar(
            update(CapabilityGap)
            .where(
                CapabilityGap.id == gap_id, CapabilityGap.company_id == self.company_id
            )
            .values(
                status=status,
                resolution_notes=resolution_notes,
                resolved_at=resolved_at,
                resolved_by_user_id=resolved_by_user_id,
            )
            .returning(CapabilityGap)
        )
