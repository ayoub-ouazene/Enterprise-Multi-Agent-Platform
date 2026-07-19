from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.departments.procurement.models import ProcurementRequest, SupplierCandidate


class ProcurementRequestRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get(
        self, request_id: UUID, *, for_update: bool = False
    ) -> ProcurementRequest | None:
        statement = select(ProcurementRequest).where(
            ProcurementRequest.request_id == request_id,
            ProcurementRequest.company_id == self.company_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def upsert(
        self, request_id: UUID, values: dict[str, object]
    ) -> ProcurementRequest:
        record = await self.get(request_id, for_update=True)
        if record is None:
            record = ProcurementRequest(
                request_id=request_id,
                company_id=self.company_id,
                **values,
            )
            self.session.add(record)
        else:
            for key, value in values.items():
                setattr(record, key, value)
        await self.session.flush()
        return record


class SupplierCandidateRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get(
        self, candidate_id: UUID, *, for_update: bool = False
    ) -> SupplierCandidate | None:
        statement = select(SupplierCandidate).where(
            SupplierCandidate.id == candidate_id,
            SupplierCandidate.company_id == self.company_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def list_for_request(
        self, request_id: UUID, *, for_update: bool = False
    ) -> list[SupplierCandidate]:
        statement = (
            select(SupplierCandidate)
            .where(
                SupplierCandidate.company_id == self.company_id,
                SupplierCandidate.request_id == request_id,
            )
            .order_by(
                SupplierCandidate.rank.asc().nulls_last(),
                SupplierCandidate.supplier_name,
                SupplierCandidate.id,
            )
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.scalars(statement)
        return list(result.all())

    async def create(self, request_id: UUID, values: dict[str, object]) -> SupplierCandidate:
        candidate = SupplierCandidate(
            company_id=self.company_id,
            request_id=request_id,
            **values,
        )
        self.session.add(candidate)
        await self.session.flush()
        return candidate

    async def update(
        self, candidate_id: UUID, values: dict[str, object]
    ) -> SupplierCandidate | None:
        candidate = await self.get(candidate_id, for_update=True)
        if candidate is None:
            return None
        for key, value in values.items():
            setattr(candidate, key, value)
        await self.session.flush()
        return candidate

    async def selected_for_request(
        self, request_id: UUID, *, for_update: bool = False
    ) -> SupplierCandidate | None:
        statement = select(SupplierCandidate).where(
            SupplierCandidate.company_id == self.company_id,
            SupplierCandidate.request_id == request_id,
            SupplierCandidate.is_selected.is_(True),
        )
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)
