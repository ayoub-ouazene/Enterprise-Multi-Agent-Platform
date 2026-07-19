from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.departments.it.enums import AssetStatus
from app.departments.it.models import AccessRequest, Asset, HardwareRequest, ITIncident, SoftwareCatalog


class TenantITRepository:
    model = None
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session, self.company_id = session, company_id

    async def get_for_request(self, request_id: UUID, *, for_update: bool = False):
        statement = select(self.model).where(self.model.request_id == request_id, self.model.company_id == self.company_id)
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def upsert(self, request_id: UUID, values: dict[str, object]):
        record = await self.get_for_request(request_id, for_update=True)
        if record is None:
            record = self.model(request_id=request_id, company_id=self.company_id, **values)
            self.session.add(record)
        else:
            for key, value in values.items():
                setattr(record, key, value)
        await self.session.flush()
        return record


class AccessRequestRepository(TenantITRepository):
    model = AccessRequest

    async def list_for_employee(self, employee_id: UUID) -> list[AccessRequest]:
        result = await self.session.scalars(select(AccessRequest).where(
            AccessRequest.company_id == self.company_id, AccessRequest.employee_id == employee_id))
        return list(result.all())


class HardwareRequestRepository(TenantITRepository):
    model = HardwareRequest


class ITIncidentRepository(TenantITRepository):
    model = ITIncident


class AssetRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session, self.company_id = session, company_id

    async def get(self, asset_id: UUID) -> Asset | None:
        return await self.session.scalar(select(Asset).where(Asset.id == asset_id, Asset.company_id == self.company_id))

    async def assigned_to(self, employee_id: UUID) -> list[Asset]:
        result = await self.session.scalars(select(Asset).where(
            Asset.company_id == self.company_id, Asset.assigned_employee_id == employee_id))
        return list(result.all())

    async def available(self, asset_type: str | None = None, *, limit: int = 20) -> list[Asset]:
        statement = select(Asset).where(Asset.company_id == self.company_id, Asset.status == AssetStatus.AVAILABLE)
        if asset_type:
            statement = statement.where(func.lower(Asset.asset_type) == asset_type.strip().lower())
        result = await self.session.scalars(statement.order_by(Asset.created_at).limit(limit))
        return list(result.all())


class SoftwareCatalogRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session, self.company_id = session, company_id

    async def get(self, software_id: UUID) -> SoftwareCatalog | None:
        return await self.session.scalar(select(SoftwareCatalog).where(
            SoftwareCatalog.id == software_id, SoftwareCatalog.company_id == self.company_id))

    async def find_active(self, name: str | None = None, *, limit: int = 20) -> list[SoftwareCatalog]:
        statement = select(SoftwareCatalog).where(
            SoftwareCatalog.company_id == self.company_id, SoftwareCatalog.is_active.is_(True))
        if name:
            escaped = name.strip().replace("%", "\\%").replace("_", "\\_")
            statement = statement.where(SoftwareCatalog.name.ilike(f"%{escaped}%", escape="\\"))
        result = await self.session.scalars(statement.order_by(SoftwareCatalog.name).limit(limit))
        return list(result.all())
