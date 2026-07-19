from app.departments.it.models import AccessRequest, Asset, HardwareRequest, ITIncident, SoftwareCatalog
import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4
from app.departments.it.repository import AssetRepository, ITIncidentRepository


def test_it_extensions_share_the_business_request_id() -> None:
    for model in (AccessRequest, HardwareRequest, ITIncident):
        assert [column.name for column in model.__table__.primary_key.columns] == ["request_id"]
        assert model.__table__.c.company_id.nullable is False


def test_assets_and_software_are_tenant_owned() -> None:
    assert Asset.__table__.c.company_id.nullable is False
    assert SoftwareCatalog.__table__.c.company_id.nullable is False
    assert "uq_assets_company_code" in {item.name for item in Asset.__table__.constraints}
    assert "uq_software_catalog_company_name" in {item.name for item in SoftwareCatalog.__table__.constraints}


def test_asset_and_incident_queries_always_include_company_scope() -> None:
    company_id, captured = uuid4(), []
    session = AsyncMock()
    async def scalar(statement):
        captured.append(statement)
        return None
    session.scalar.side_effect = scalar
    asyncio.run(AssetRepository(session, company_id).get(uuid4()))
    asyncio.run(ITIncidentRepository(session, company_id).get_for_request(uuid4()))
    for statement in captured:
        sql = str(statement)
        assert "company_id" in sql
        assert company_id in statement.compile().params.values()
