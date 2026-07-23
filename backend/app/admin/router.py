"""Admin router - Company Administration API."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.dependencies import (
    require_company_account,
    require_company_or_any_manager,
    require_finance_admin,
    require_hr_admin,
    require_it_admin,
    require_procurement_admin,
)
from app.admin.schemas import (
    AdminAssetCreate,
    AdminAssetResponse,
    AdminAssetUpdate,
    AdminBudgetCreate,
    AdminBudgetResponse,
    AdminBudgetUpdate,
    AdminDepartmentResponse,
    AdminDepartmentUpdate,
    AdminEmployeeCreate,
    AdminEmployeeResponse,
    AdminEmployeeUpdate,
    AdminHolidayCreate,
    AdminHolidayResponse,
    AdminHolidayUpdate,
    AdminLeaveBalanceCreate,
    AdminLeaveBalanceResponse,
    AdminLeaveBalanceUpdate,
    AdminOnboardingStatusResponse,
    AdminPolicyReadinessResponse,
    AdminSoftwareCatalogCreate,
    AdminSoftwareCatalogResponse,
    AdminSoftwareCatalogUpdate,
    AdminStaffingRuleCreate,
    AdminStaffingRuleResponse,
    AdminStaffingRuleUpdate,
    AdminSupplierCreate,
    AdminSupplierResponse,
    AdminSupplierUpdate,
)
from app.admin.service import (
    AdminAssetService,
    AdminBudgetService,
    AdminDepartmentService,
    AdminEmployeeService,
    AdminHolidayService,
    AdminLeaveBalanceService,
    AdminSoftwareCatalogService,
    AdminStaffingRuleService,
    AdminSupplierService,
    OptimisticLockError,
)
from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType, DepartmentType
from app.core.exceptions import (
    BusinessValidationError,
    ConflictError,
    NotFoundError,
)
from app.database.session import get_db_session
from app.onboarding.models import ImportJob
from app.onboarding.service import CompanyOnboardingService
from app.rag.enums import (
    KnowledgeDepartmentScope,
    KnowledgeDocumentType,
    KnowledgeIngestionStatus,
)
from app.rag.models import KnowledgeDocument

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _handle_admin_exceptions(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    if isinstance(exc, (BusinessValidationError, OptimisticLockError)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    raise exc


# =========================================================================
# 1. Employee Directory
# =========================================================================


@router.get("/employees", response_model=list[AdminEmployeeResponse])
async def list_employees(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
    department_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AdminEmployeeResponse]:
    service = AdminEmployeeService(session, current_user.company_id)
    records = await service.list(
        department_id=department_id, limit=limit, offset=offset
    )
    return [AdminEmployeeResponse.model_validate(r) for r in records]


@router.post(
    "/employees",
    response_model=AdminEmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_employee(
    payload: AdminEmployeeCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_account)
    ],
) -> AdminEmployeeResponse:
    service = AdminEmployeeService(session, current_user.company_id)
    try:
        record = await service.create(payload, current_user)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminEmployeeResponse.model_validate(record)


@router.get("/employees/{employee_id}", response_model=AdminEmployeeResponse)
async def get_employee(
    employee_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
) -> AdminEmployeeResponse:
    service = AdminEmployeeService(session, current_user.company_id)
    try:
        record = await service.get(employee_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found"
        )
    return AdminEmployeeResponse.model_validate(record)


@router.patch("/employees/{employee_id}", response_model=AdminEmployeeResponse)
async def update_employee(
    employee_id: UUID,
    payload: AdminEmployeeUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
) -> AdminEmployeeResponse:
    service = AdminEmployeeService(session, current_user.company_id)
    try:
        record = await service.update(employee_id, payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminEmployeeResponse.model_validate(record)


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_employee(
    employee_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_account)
    ],
) -> None:
    service = AdminEmployeeService(session, current_user.company_id)
    try:
        await service.soft_delete(employee_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)


# =========================================================================
# 2. Department Configuration
# =========================================================================


@router.get("/departments", response_model=list[AdminDepartmentResponse])
async def list_departments(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
) -> list[AdminDepartmentResponse]:
    service = AdminDepartmentService(session, current_user.company_id)
    records = await service.list()
    return [AdminDepartmentResponse.model_validate(r) for r in records]


@router.get("/departments/{department_id}", response_model=AdminDepartmentResponse)
async def get_department(
    department_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
) -> AdminDepartmentResponse:
    service = AdminDepartmentService(session, current_user.company_id)
    try:
        record = await service.get(department_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminDepartmentResponse.model_validate(record)


@router.patch(
    "/departments/{department_id}", response_model=AdminDepartmentResponse
)
async def update_department(
    department_id: UUID,
    payload: AdminDepartmentUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_account)
    ],
) -> AdminDepartmentResponse:
    service = AdminDepartmentService(session, current_user.company_id)
    try:
        record = await service.update(department_id, payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminDepartmentResponse.model_validate(record)


# =========================================================================
# 3. Asset Inventory (scoped IT admin)
# =========================================================================


@router.get("/assets", response_model=list[AdminAssetResponse])
async def list_assets(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
    asset_type: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AdminAssetResponse]:
    service = AdminAssetService(session, current_user.company_id)
    records = await service.list(
        asset_type=asset_type, limit=limit, offset=offset
    )
    return [AdminAssetResponse.model_validate(r) for r in records]


@router.post(
    "/assets",
    response_model=AdminAssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_asset(
    payload: AdminAssetCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_it_admin)],
) -> AdminAssetResponse:
    service = AdminAssetService(session, current_user.company_id)
    try:
        record = await service.create(payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminAssetResponse.model_validate(record)


@router.get("/assets/{asset_id}", response_model=AdminAssetResponse)
async def get_asset(
    asset_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
) -> AdminAssetResponse:
    service = AdminAssetService(session, current_user.company_id)
    try:
        record = await service.get(asset_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminAssetResponse.model_validate(record)


@router.patch("/assets/{asset_id}", response_model=AdminAssetResponse)
async def update_asset(
    asset_id: UUID,
    payload: AdminAssetUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_it_admin)],
) -> AdminAssetResponse:
    service = AdminAssetService(session, current_user.company_id)
    try:
        record = await service.update(asset_id, payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminAssetResponse.model_validate(record)


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_asset(
    asset_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_it_admin)],
) -> None:
    service = AdminAssetService(session, current_user.company_id)
    try:
        await service.soft_delete(asset_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)


# =========================================================================
# 4. Software Catalog (scoped IT admin)
# =========================================================================


@router.get(
    "/software-catalog", response_model=list[AdminSoftwareCatalogResponse]
)
async def list_software_catalog(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
    is_active: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AdminSoftwareCatalogResponse]:
    service = AdminSoftwareCatalogService(session, current_user.company_id)
    records = await service.list(
        is_active=is_active, limit=limit, offset=offset
    )
    return [AdminSoftwareCatalogResponse.model_validate(r) for r in records]


@router.post(
    "/software-catalog",
    response_model=AdminSoftwareCatalogResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_software_catalog(
    payload: AdminSoftwareCatalogCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_it_admin)],
) -> AdminSoftwareCatalogResponse:
    service = AdminSoftwareCatalogService(session, current_user.company_id)
    try:
        record = await service.create(payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminSoftwareCatalogResponse.model_validate(record)


@router.get(
    "/software-catalog/{software_id}",
    response_model=AdminSoftwareCatalogResponse,
)
async def get_software_catalog(
    software_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
) -> AdminSoftwareCatalogResponse:
    service = AdminSoftwareCatalogService(session, current_user.company_id)
    try:
        record = await service.get(software_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminSoftwareCatalogResponse.model_validate(record)


@router.patch(
    "/software-catalog/{software_id}",
    response_model=AdminSoftwareCatalogResponse,
)
async def update_software_catalog(
    software_id: UUID,
    payload: AdminSoftwareCatalogUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_it_admin)],
) -> AdminSoftwareCatalogResponse:
    service = AdminSoftwareCatalogService(session, current_user.company_id)
    try:
        record = await service.update(software_id, payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminSoftwareCatalogResponse.model_validate(record)


@router.delete(
    "/software-catalog/{software_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def soft_delete_software_catalog(
    software_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_it_admin)],
) -> None:
    service = AdminSoftwareCatalogService(session, current_user.company_id)
    try:
        await service.soft_delete(software_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)


# =========================================================================
# 5. Budget Management (scoped Finance admin)
# =========================================================================


@router.get('/budgets', response_model=list[AdminBudgetResponse])
async def list_budgets(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
    department_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AdminBudgetResponse]:
    service = AdminBudgetService(session, current_user.company_id)
    records = await service.list(
        department_id=department_id, limit=limit, offset=offset
    )
    return [AdminBudgetResponse.model_validate(r) for r in records]


@router.post(
    '/budgets',
    response_model=AdminBudgetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_budget(
    payload: AdminBudgetCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_finance_admin)],
) -> AdminBudgetResponse:
    service = AdminBudgetService(session, current_user.company_id)
    try:
        record = await service.create(payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminBudgetResponse.model_validate(record)


@router.get('/budgets/{budget_id}', response_model=AdminBudgetResponse)
async def get_budget(
    budget_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
) -> AdminBudgetResponse:
    service = AdminBudgetService(session, current_user.company_id)
    try:
        record = await service.get(budget_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminBudgetResponse.model_validate(record)


@router.patch('/budgets/{budget_id}', response_model=AdminBudgetResponse)
async def update_budget(
    budget_id: UUID,
    payload: AdminBudgetUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_finance_admin)],
) -> AdminBudgetResponse:
    service = AdminBudgetService(session, current_user.company_id)
    try:
        record = await service.update(budget_id, payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminBudgetResponse.model_validate(record)


@router.delete('/budgets/{budget_id}', status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_budget(
    budget_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_finance_admin)],
) -> None:
    service = AdminBudgetService(session, current_user.company_id)
    try:
        await service.soft_delete(budget_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)


# =========================================================================
# 6. Leave Balances (scoped HR admin)
# =========================================================================


@router.get(
    '/employees/{employee_id}/leave-balances',
    response_model=list[AdminLeaveBalanceResponse],
)
async def list_leave_balances(
    employee_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
) -> list[AdminLeaveBalanceResponse]:
    service = AdminLeaveBalanceService(session, current_user.company_id)
    records = await service.list_for_employee(employee_id)
    return [AdminLeaveBalanceResponse.model_validate(r) for r in records]


@router.post(
    '/leave-balances',
    response_model=AdminLeaveBalanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_leave_balance(
    payload: AdminLeaveBalanceCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_hr_admin)],
) -> AdminLeaveBalanceResponse:
    service = AdminLeaveBalanceService(session, current_user.company_id)
    try:
        record = await service.create(payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminLeaveBalanceResponse.model_validate(record)


@router.get(
    '/leave-balances/{balance_id}', response_model=AdminLeaveBalanceResponse
)
async def get_leave_balance(
    balance_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
) -> AdminLeaveBalanceResponse:
    service = AdminLeaveBalanceService(session, current_user.company_id)
    try:
        record = await service.get(balance_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminLeaveBalanceResponse.model_validate(record)


@router.patch(
    '/leave-balances/{balance_id}', response_model=AdminLeaveBalanceResponse
)
async def update_leave_balance(
    balance_id: UUID,
    payload: AdminLeaveBalanceUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_hr_admin)],
) -> AdminLeaveBalanceResponse:
    service = AdminLeaveBalanceService(session, current_user.company_id)
    try:
        record = await service.update(balance_id, payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminLeaveBalanceResponse.model_validate(record)


@router.delete(
    '/leave-balances/{balance_id}', status_code=status.HTTP_204_NO_CONTENT
)
async def delete_leave_balance(
    balance_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_hr_admin)],
) -> None:
    service = AdminLeaveBalanceService(session, current_user.company_id)
    try:
        await service.delete(balance_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)


# =========================================================================
# 7. Company Holidays (scoped HR admin)
# =========================================================================


@router.get('/holidays', response_model=list[AdminHolidayResponse])
async def list_holidays(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
    year: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AdminHolidayResponse]:
    service = AdminHolidayService(session, current_user.company_id)
    records = await service.list(year=year, limit=limit, offset=offset)
    return [AdminHolidayResponse.model_validate(r) for r in records]


@router.post(
    '/holidays',
    response_model=AdminHolidayResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_holiday(
    payload: AdminHolidayCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_hr_admin)],
) -> AdminHolidayResponse:
    service = AdminHolidayService(session, current_user.company_id)
    try:
        record = await service.create(payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminHolidayResponse.model_validate(record)


@router.get('/holidays/{holiday_id}', response_model=AdminHolidayResponse)
async def get_holiday(
    holiday_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
) -> AdminHolidayResponse:
    service = AdminHolidayService(session, current_user.company_id)
    try:
        record = await service.get(holiday_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminHolidayResponse.model_validate(record)


@router.patch('/holidays/{holiday_id}', response_model=AdminHolidayResponse)
async def update_holiday(
    holiday_id: UUID,
    payload: AdminHolidayUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_hr_admin)],
) -> AdminHolidayResponse:
    service = AdminHolidayService(session, current_user.company_id)
    try:
        record = await service.update(holiday_id, payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminHolidayResponse.model_validate(record)


@router.delete('/holidays/{holiday_id}', status_code=status.HTTP_204_NO_CONTENT)
async def hard_delete_holiday(
    holiday_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_hr_admin)],
) -> None:
    service = AdminHolidayService(session, current_user.company_id)
    try:
        await service.hard_delete(holiday_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)


# =========================================================================
# 8. Staffing Rules (scoped HR admin)
# =========================================================================


@router.get('/staffing-rules', response_model=list[AdminStaffingRuleResponse])
async def list_staffing_rules(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
    department_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AdminStaffingRuleResponse]:
    service = AdminStaffingRuleService(session, current_user.company_id)
    records = await service.list(
        department_id=department_id, limit=limit, offset=offset
    )
    return [AdminStaffingRuleResponse.model_validate(r) for r in records]


@router.post(
    '/staffing-rules',
    response_model=AdminStaffingRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_staffing_rule(
    payload: AdminStaffingRuleCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_hr_admin)],
) -> AdminStaffingRuleResponse:
    service = AdminStaffingRuleService(session, current_user.company_id)
    try:
        record = await service.create(payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminStaffingRuleResponse.model_validate(record)


@router.get(
    '/staffing-rules/{rule_id}', response_model=AdminStaffingRuleResponse
)
async def get_staffing_rule(
    rule_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
) -> AdminStaffingRuleResponse:
    service = AdminStaffingRuleService(session, current_user.company_id)
    try:
        record = await service.get(rule_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminStaffingRuleResponse.model_validate(record)


@router.patch(
    '/staffing-rules/{rule_id}', response_model=AdminStaffingRuleResponse
)
async def update_staffing_rule(
    rule_id: UUID,
    payload: AdminStaffingRuleUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_hr_admin)],
) -> AdminStaffingRuleResponse:
    service = AdminStaffingRuleService(session, current_user.company_id)
    try:
        record = await service.update(rule_id, payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminStaffingRuleResponse.model_validate(record)


@router.delete(
    '/staffing-rules/{rule_id}', status_code=status.HTTP_204_NO_CONTENT
)
async def hard_delete_staffing_rule(
    rule_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_hr_admin)],
) -> None:
    service = AdminStaffingRuleService(session, current_user.company_id)
    try:
        await service.hard_delete(rule_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)


# =========================================================================
# 9. Supplier Directory (scoped Procurement admin)
# =========================================================================


@router.get('/suppliers', response_model=list[AdminSupplierResponse])
async def list_suppliers(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
    is_active: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AdminSupplierResponse]:
    service = AdminSupplierService(session, current_user.company_id)
    records = await service.list(
        is_active=is_active, limit=limit, offset=offset
    )
    return [AdminSupplierResponse.model_validate(r) for r in records]


@router.post(
    '/suppliers',
    response_model=AdminSupplierResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_supplier(
    payload: AdminSupplierCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_procurement_admin)
    ],
) -> AdminSupplierResponse:
    service = AdminSupplierService(session, current_user.company_id)
    try:
        record = await service.create(payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminSupplierResponse.model_validate(record)


@router.get('/suppliers/{supplier_id}', response_model=AdminSupplierResponse)
async def get_supplier(
    supplier_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
) -> AdminSupplierResponse:
    service = AdminSupplierService(session, current_user.company_id)
    try:
        record = await service.get(supplier_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminSupplierResponse.model_validate(record)


@router.patch(
    '/suppliers/{supplier_id}', response_model=AdminSupplierResponse
)
async def update_supplier(
    supplier_id: UUID,
    payload: AdminSupplierUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_procurement_admin)
    ],
) -> AdminSupplierResponse:
    service = AdminSupplierService(session, current_user.company_id)
    try:
        record = await service.update(supplier_id, payload)
    except Exception as exc:
        _handle_admin_exceptions(exc)
    return AdminSupplierResponse.model_validate(record)


@router.delete(
    '/suppliers/{supplier_id}', status_code=status.HTTP_204_NO_CONTENT
)
async def soft_delete_supplier(
    supplier_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_procurement_admin)
    ],
) -> None:
    service = AdminSupplierService(session, current_user.company_id)
    try:
        await service.soft_delete(supplier_id)
    except Exception as exc:
        _handle_admin_exceptions(exc)


# =========================================================================
# 10. Policy Readiness
# =========================================================================


@router.get('/policy-readiness', response_model=AdminPolicyReadinessResponse)
async def get_policy_readiness(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
) -> AdminPolicyReadinessResponse:
    company_id = current_user.company_id
    total = await session.scalar(
        select(func.count(KnowledgeDocument.id)).where(
            KnowledgeDocument.company_id == company_id
        )
    )
    ingested = await session.scalar(
        select(func.count(KnowledgeDocument.id)).where(
            KnowledgeDocument.company_id == company_id,
            KnowledgeDocument.is_active.is_(True),
            KnowledgeDocument.ingestion_status == KnowledgeIngestionStatus.COMPLETED,
            KnowledgeDocument.document_type == KnowledgeDocumentType.POLICY,
        )
    )
    docs = await session.scalars(
        select(KnowledgeDocument).where(
            KnowledgeDocument.company_id == company_id,
            KnowledgeDocument.is_active.is_(True),
            KnowledgeDocument.ingestion_status == KnowledgeIngestionStatus.COMPLETED,
        )
    )
    coverage: dict[str, bool] = {d.value: False for d in DepartmentType}
    for doc in docs.all():
        for scope in doc.department_scope:
            val = scope.value
            if val == 'shared':
                for k in coverage:
                    coverage[k] = True
            else:
                coverage[val] = True

    return AdminPolicyReadinessResponse(
        total_documents=total or 0,
        ingested_active_policies=ingested or 0,
        department_coverage=coverage,
        ready=all(coverage.values()) and (ingested or 0) > 0,
    )


# =========================================================================
# 11. Onboarding Status
# =========================================================================


@router.get('/onboarding-status', response_model=AdminOnboardingStatusResponse)
async def get_admin_onboarding_status(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_company_or_any_manager)
    ],
) -> AdminOnboardingStatusResponse:
    from app.companies.models import Company

    company = await session.scalar(
        select(Company).where(Company.id == current_user.company_id)
    )
    is_active = bool(company and company.is_active)

    last_job = await session.scalar(
        select(ImportJob)
        .where(ImportJob.company_id == current_user.company_id)
        .order_by(ImportJob.created_at.desc())
    )

    onboarding = CompanyOnboardingService(
        session, current_user.company_id
    )
    try:
        status_obj = await onboarding.get_status()
        onboarding_complete = status_obj.can_activate
    except Exception:
        onboarding_complete = False

    return AdminOnboardingStatusResponse(
        company_id=current_user.company_id,
        is_active=is_active,
        onboarding_complete=onboarding_complete,
        last_import_job=last_job.id if last_job else None,
        last_import_at=last_job.created_at if last_job else None,
    )

