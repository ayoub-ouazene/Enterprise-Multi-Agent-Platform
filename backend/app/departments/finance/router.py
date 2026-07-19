from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.enums import ActorType, DepartmentType
from app.database.session import get_db_session
from app.departments.finance.repository import BudgetRepository, FinancialTransactionRepository
from app.departments.finance.schemas import BudgetResponse, FinancialTransactionResponse
from app.departments.repository import DepartmentRepository


router = APIRouter(tags=["finance"])


async def _finance_manager(
    session: AsyncSession, current_user: AuthenticatedUser
) -> bool:
    if (
        current_user.actor_type != ActorType.DEPARTMENT_MANAGER
        or not current_user.is_manager
        or current_user.department_id is None
    ):
        return False
    department = await DepartmentRepository(session, current_user.company_id).get_by_id(
        current_user.department_id
    )
    return bool(
        department is not None
        and department.is_active
        and department.department_type == DepartmentType.FINANCE
    )


async def _require_financial_reader(
    session: AsyncSession, current_user: AuthenticatedUser
) -> None:
    if current_user.actor_type == ActorType.COMPANY:
        return
    if await _finance_manager(session, current_user):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("/api/v1/budgets", response_model=list[BudgetResponse])
async def list_budgets(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[BudgetResponse]:
    repository = BudgetRepository(session, current_user.company_id)
    if current_user.actor_type == ActorType.COMPANY or await _finance_manager(
        session, current_user
    ):
        records = await repository.list(limit=limit, offset=offset)
    elif (
        current_user.actor_type == ActorType.DEPARTMENT_MANAGER
        and current_user.is_manager
        and current_user.department_id is not None
    ):
        records = await repository.list(
            department_id=current_user.department_id, limit=limit, offset=offset
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    return [BudgetResponse.model_validate(item) for item in records]


@router.get("/api/v1/budgets/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> BudgetResponse:
    record = await BudgetRepository(session, current_user.company_id).get(budget_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    broad_access = current_user.actor_type == ActorType.COMPANY or await _finance_manager(
        session, current_user
    )
    own_department = (
        current_user.actor_type == ActorType.DEPARTMENT_MANAGER
        and current_user.is_manager
        and current_user.department_id == record.department_id
    )
    if not broad_access and not own_department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return BudgetResponse.model_validate(record)


@router.get(
    "/api/v1/financial-transactions",
    response_model=list[FinancialTransactionResponse],
)
async def list_financial_transactions(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    budget_id: Annotated[UUID | None, Query()] = None,
    request_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[FinancialTransactionResponse]:
    await _require_financial_reader(session, current_user)
    records = await FinancialTransactionRepository(
        session, current_user.company_id
    ).list(budget_id=budget_id, request_id=request_id, limit=limit, offset=offset)
    return [FinancialTransactionResponse.model_validate(item) for item in records]


@router.get(
    "/api/v1/financial-transactions/{transaction_id}",
    response_model=FinancialTransactionResponse,
)
async def get_financial_transaction(
    transaction_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> FinancialTransactionResponse:
    await _require_financial_reader(session, current_user)
    record = await FinancialTransactionRepository(
        session, current_user.company_id
    ).get(transaction_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial transaction not found",
        )
    return FinancialTransactionResponse.model_validate(record)
