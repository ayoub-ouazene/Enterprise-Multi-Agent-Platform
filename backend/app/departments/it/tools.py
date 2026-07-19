from typing import Any

from app.departments.contracts import DepartmentToolRequest
from app.departments.it.repository import AssetRepository, SoftwareCatalogRepository


class ITToolService:
    """Allowlisted read-only IT database tools; it never commits or mutates records."""

    def __init__(self, assets: AssetRepository, software: SoftwareCatalogRepository) -> None:
        self.assets, self.software = assets, software

    async def execute(self, request: DepartmentToolRequest) -> dict[str, Any]:
        if request.operation == "check_asset_inventory":
            records = await self.assets.available(request.arguments.get("asset_type"))
            return {"operation": request.operation, "available_count": len(records),
                "candidates": [{"asset_id": str(item.id), "asset_type": item.asset_type,
                    "brand": item.brand, "model": item.model, "location": item.location} for item in records]}
        if request.operation == "check_software_availability":
            records = await self.software.find_active(request.arguments.get("software_name"))
            return {"operation": request.operation, "matches": [{"software_id": str(item.id),
                "name": item.name, "access_type": item.access_type,
                "requires_manager_approval": item.requires_manager_approval,
                "requires_it_approval": item.requires_it_approval,
                "license_available": (not item.license_limited or (item.available_license_count or 0) > 0)} for item in records]}
        raise ValueError("IT tool operation is not allowlisted")
