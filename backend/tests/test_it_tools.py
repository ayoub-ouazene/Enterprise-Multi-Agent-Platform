import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from app.departments.contracts import DepartmentToolRequest
from app.departments.it.tools import ITToolService


def request(operation, arguments):
    return DepartmentToolRequest(tool_name="it_data", operation=operation, arguments=arguments,
        reason="Trusted IT lookup is required.", expected_result_type="structured_lookup")


def test_inventory_and_software_checks_return_safe_tenant_data() -> None:
    assets, software = AsyncMock(), AsyncMock()
    assets.available.return_value = [SimpleNamespace(id=uuid4(), asset_type="laptop", brand="A",
        model="M", location="HQ")]
    software.find_active.return_value = [SimpleNamespace(id=uuid4(), name="Editor", access_type="licensed",
        requires_manager_approval=True, requires_it_approval=True, license_limited=True,
        available_license_count=2)]
    service = ITToolService(assets, software)
    inventory = asyncio.run(service.execute(request("check_asset_inventory", {"asset_type": "laptop"})))
    availability = asyncio.run(service.execute(request("check_software_availability", {"software_name": "Editor"})))
    assert inventory["available_count"] == 1 and "serial_number" not in str(inventory)
    assert availability["matches"][0]["license_available"] is True


def test_unapproved_it_tool_is_rejected() -> None:
    with pytest.raises(ValueError, match="not allowlisted"):
        asyncio.run(ITToolService(AsyncMock(), AsyncMock()).execute(request("prepare_password_reset", {})))
