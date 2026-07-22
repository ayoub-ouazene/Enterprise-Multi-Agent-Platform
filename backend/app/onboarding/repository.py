from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.onboarding.enums import ImportJobStatus, ImportType
from app.onboarding.models import ImportJob


class ImportJobRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get_by_id(self, job_id: UUID) -> ImportJob | None:
        return await self.session.scalar(
            select(ImportJob).where(
                ImportJob.id == job_id,
                ImportJob.company_id == self.company_id,
            )
        )

    async def create(
        self,
        *,
        import_type: ImportType,
        original_filename: str,
        uploaded_by_user_id: UUID,
        checksum: str,
        idempotency_key: str | None,
        total_rows: int = 0,
        validation_report: dict[str, object] | None = None,
    ) -> ImportJob:
        job = ImportJob(
            company_id=self.company_id,
            import_type=import_type,
            status=ImportJobStatus.PENDING,
            original_filename=original_filename,
            uploaded_by_user_id=uploaded_by_user_id,
            total_rows=total_rows,
            checksum=checksum,
            idempotency_key=idempotency_key,
            validation_report=validation_report or {},
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def update_status(
        self,
        job_id: UUID,
        status: ImportJobStatus,
        **kwargs: object,
    ) -> ImportJob | None:
        values: dict[str, object] = {"status": status}
        if status == ImportJobStatus.PROCESSING and kwargs.get("started_at") is None:
            values["started_at"] = datetime.now(UTC)
        if status in (ImportJobStatus.COMPLETED, ImportJobStatus.PARTIALLY_COMPLETED) and kwargs.get("completed_at") is None:
            values["completed_at"] = datetime.now(UTC)
        if status == ImportJobStatus.FAILED and kwargs.get("failed_at") is None:
            values["failed_at"] = datetime.now(UTC)
        for key, value in kwargs.items():
            values[key] = value
        statement = (
            update(ImportJob)
            .where(
                ImportJob.id == job_id,
                ImportJob.company_id == self.company_id,
            )
            .values(**values)
            .returning(ImportJob)
        )
        return await self.session.scalar(statement)

    async def find_existing_completed(
        self,
        import_type: ImportType,
        checksum: str,
    ) -> ImportJob | None:
        return await self.session.scalar(
            select(ImportJob).where(
                ImportJob.company_id == self.company_id,
                ImportJob.import_type == import_type,
                ImportJob.checksum == checksum,
                ImportJob.status == ImportJobStatus.COMPLETED,
            )
        )

    async def list(
        self,
        import_type: ImportType | None,
        status: ImportJobStatus | None,
        limit: int,
        offset: int,
    ) -> list[ImportJob]:
        statement = select(ImportJob).where(
            ImportJob.company_id == self.company_id
        )
        if import_type is not None:
            statement = statement.where(ImportJob.import_type == import_type)
        if status is not None:
            statement = statement.where(ImportJob.status == status)
        result = await self.session.scalars(
            statement.order_by(ImportJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())
