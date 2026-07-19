from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.enums import DepartmentType
from app.departments.contracts import (
    DepartmentExecutionContext,
    DepartmentExecutionResult,
    DepartmentExecutionStatus,
    DepartmentExecutionUpdates,
    DepartmentHumanActionUpdates,
    DepartmentResultUpdates,
    DepartmentRoutingUpdates,
    DepartmentStateUpdates,
)
from app.departments.customer_support.service import requester_access_scopes
from app.departments.finance.enums import (
    BudgetStatus,
    FinanceModelRole,
)
from app.departments.finance.model_policy import initial_model_role, requires_reasoning_pass
from app.departments.finance.repository import (
    BudgetRepository,
    FinanceRequestRepository,
    FinancialTransactionRepository,
)
from app.departments.finance.schemas import FinanceDepartmentResult, FinanceExecutionInput
from app.departments.finance.tools import FinanceOperationError, money
from app.llm.groq import GroqFinanceClient
from app.rag.enums import KnowledgeDepartmentScope
from app.rag.retrieval import KnowledgeRetrievalService
from app.rag.schemas import KnowledgeRetrievalQuery


class FinanceService:
    def __init__(
        self,
        session: AsyncSession,
        requester: AuthenticatedUser,
        settings: Settings,
        retrieval: KnowledgeRetrievalService,
        *,
        llm_client: Any | None = None,
        budget_repository: BudgetRepository | None = None,
        finance_request_repository: FinanceRequestRepository | None = None,
        transaction_repository: FinancialTransactionRepository | None = None,
    ) -> None:
        self.session = session
        self.requester = requester
        self.settings = settings
        self.retrieval = retrieval
        self.llm = llm_client or GroqFinanceClient(settings)
        self.budgets = budget_repository or BudgetRepository(session, requester.company_id)
        self.finance_requests = finance_request_repository or FinanceRequestRepository(
            session, requester.company_id
        )
        self.transactions = transaction_repository or FinancialTransactionRepository(
            session, requester.company_id
        )

    async def execute(self, context: DepartmentExecutionContext) -> DepartmentExecutionResult:
        model_input, budget = await self._build_input(context)
        await self.session.rollback()
        evidence = await self.retrieval.search_trusted(
            KnowledgeRetrievalQuery(
                company_id=context.company_id,
                query_text=self._query(context),
                departments=[
                    KnowledgeDepartmentScope.FINANCE,
                    KnowledgeDepartmentScope.SHARED,
                ],
                allowed_access_scopes=requester_access_scopes(
                    AuthenticatedUser(
                        user_id=context.requester_user_id,
                        company_id=context.company_id,
                        email="trusted-requester@internal.invalid",
                        actor_type=context.requester_actor_type,
                        employee_id=context.requester_employee_id,
                        department_id=context.requester_department_id,
                        is_manager=context.requester_is_manager,
                    )
                ),
                top_k=self.settings.rag_top_k,
            )
        )
        await self.session.rollback()
        model_input = model_input.model_copy(
            update={"evidence": [self._evidence(item) for item in evidence]}
        )
        role = initial_model_role(model_input)
        result = await self.llm.generate(model_input, role=role)
        if requires_reasoning_pass(result, role):
            result = await self.llm.generate(model_input, role=FinanceModelRole.REASONING)
        self._validate(result, evidence, model_input, budget)
        return self._to_department_result(result)

    async def _build_input(self, context: DepartmentExecutionContext) -> tuple[FinanceExecutionInput, Any]:
        payload = context.collaboration_input.payload if context.collaboration_input else {}
        custom = context.relevant_custom_data
        amount = self._optional_money(payload.get("estimated_cost", payload.get("quoted_amount", custom.get("requested_amount"))))
        currency = payload.get("currency", custom.get("currency"))
        budget_id = self._uuid(payload.get("budget_id", custom.get("budget_id")))
        budget = await self.budgets.get(budget_id) if budget_id else None
        if budget is None and budget_id is None:
            candidates = await self.budgets.find_current(
                department_id=context.requester_department_id,
                currency=str(currency).upper() if currency else None,
                on_date=date.today(),
            )
            if len(candidates) == 1:
                budget = candidates[0]
        transactions = (
            await self.transactions.list(budget_id=budget.id, limit=10) if budget else []
        )
        budget_data = self._budget_data(budget) if budget else {}
        origin = context.collaboration_input.sender_department if context.collaboration_input else None
        return FinanceExecutionInput(
            request_id=context.request_id,
            company_id=context.company_id,
            requester_user_id=context.requester_user_id,
            requester_employee_id=context.requester_employee_id,
            requester_department_id=context.requester_department_id,
            requester_actor_type=context.requester_actor_type,
            requester_is_manager=context.requester_is_manager,
            owner_department_type=context.owner_department_type,
            active_department_type=context.active_department_type,
            originating_department_type=origin,
            request_type=context.request_type,
            original_summary=context.request_summary,
            latest_user_input=context.latest_user_input,
            current_stage=context.current_stage,
            requested_amount=amount,
            currency=str(currency).upper() if currency else None,
            budget=budget_data,
            cost_center=payload.get("cost_center", custom.get("cost_center")),
            relevant_transactions=[{
                "type": item.transaction_type.value,
                "amount": str(item.amount),
                "currency": item.currency,
                "status": item.status.value,
                "reference": item.reference,
            } for item in transactions],
            business_justification=payload.get(
                "business_reason", payload.get("business_justification", context.request_summary)
            ),
            urgency=payload.get("urgency", custom.get("urgency")),
            supplier_context=self._supplier_context(payload),
            approval_state=(
                context.human_response.model_dump(mode="json")
                if context.human_response else {}
            ),
            collaboration_input=context.collaboration_input,
            collaboration_result=context.collaboration_result,
            tool_results=context.tool_results,
            previous_finance_state=context.department_data,
        ), budget

    @staticmethod
    def _optional_money(value: Any) -> Decimal | None:
        if value in (None, ""):
            return None
        return money(value)

    @staticmethod
    def _uuid(value: Any) -> UUID | None:
        if value in (None, ""):
            return None
        try:
            return UUID(str(value))
        except ValueError:
            raise FinanceOperationError("invalid budget reference") from None

    @staticmethod
    def _supplier_context(payload: dict[str, Any]) -> dict[str, Any]:
        allowed = ("candidate_summary", "shortlist_summary", "quantity", "delivery_cost", "taxes")
        return {key: payload[key] for key in allowed if key in payload}

    @staticmethod
    def _budget_data(budget: Any) -> dict[str, Any]:
        return {
            "budget_id": str(budget.id),
            "safe_reference": budget.name,
            "department_id": str(budget.department_id) if budget.department_id else None,
            "currency": budget.currency,
            "status": budget.status.value,
            "period_start": budget.period_start.isoformat(),
            "period_end": budget.period_end.isoformat(),
            "allocated_amount": str(budget.allocated_amount),
            "reserved_amount": str(budget.reserved_amount),
            "committed_amount": str(budget.committed_amount),
            "spent_amount": str(budget.spent_amount),
            "available_amount": str(budget.available_amount),
            "approval_threshold": (
                str(budget.approval_threshold) if budget.approval_threshold is not None else None
            ),
        }

    @staticmethod
    def _query(context: DepartmentExecutionContext) -> str:
        parts = [context.request_summary, context.latest_user_input or ""]
        if context.collaboration_input:
            payload = context.collaboration_input.payload
            parts.extend(str(payload.get(key, "")) for key in (
                "business_reason", "business_justification", "requested_asset",
                "candidate_summary", "shortlist_summary",
            ))
        return "\n".join(part for part in parts if part)[:2000]

    @staticmethod
    def _evidence(item: Any) -> dict[str, Any]:
        return {
            "document_id": str(item.document_id),
            "title": item.title,
            "document_type": item.document_type.value,
            "version": item.version,
            "chunk_index": item.chunk_index,
            "effective_date": item.effective_date.isoformat() if item.effective_date else None,
            "content": item.chunk_text,
        }

    @staticmethod
    def _validate(
        result: FinanceDepartmentResult,
        evidence: list[Any],
        context: FinanceExecutionInput,
        budget: Any,
    ) -> None:
        allowed = {
            (item.document_id, item.title, item.document_type, item.version, item.chunk_index)
            for item in evidence
        }
        if any(
            (source.document_id, source.title, source.document_type, source.version, source.chunk_index)
            not in allowed
            for source in result.sources_used
        ):
            raise ValueError("Finance returned an unauthorized source reference")
        if result.clarification_question and (
            result.clarification_question
            == context.previous_finance_state.get("clarification_question")
        ):
            raise ValueError("Finance repeated a clarification question")
        if budget is None:
            if result.available_budget is not None or result.budget_sufficient is not None:
                raise ValueError("Finance invented budget facts")
            return
        actual_available = budget.available_amount
        if result.available_budget is not None and result.available_budget != actual_available:
            raise ValueError("Finance balance conflicts with deterministic budget data")
        if context.requested_amount is not None:
            sufficient = (
                budget.status == BudgetStatus.ACTIVE
                and budget.period_start <= date.today() <= budget.period_end
                and context.currency == budget.currency
                and context.requested_amount <= actual_available
            )
            if result.budget_sufficient is not None and result.budget_sufficient != sufficient:
                raise ValueError("Finance sufficiency conflicts with deterministic calculation")
            threshold = budget.approval_threshold
            if threshold is not None and context.requested_amount > threshold and not result.approval_required:
                raise ValueError("Finance omitted required threshold approval")
        if budget.status == BudgetStatus.FROZEN and not result.approval_required:
            raise ValueError("A frozen budget requires human approval")

    @staticmethod
    def _to_department_result(result: FinanceDepartmentResult) -> DepartmentExecutionResult:
        status = {
            "wait_for_user_input": DepartmentExecutionStatus.WAITING_FOR_USER,
            "execute_tool": DepartmentExecutionStatus.WAITING_FOR_TOOL,
            "request_human_action": DepartmentExecutionStatus.WAITING_FOR_HUMAN,
            "fail_request": DepartmentExecutionStatus.UNSUPPORTED,
        }.get(result.next_action.value, DepartmentExecutionStatus.COMPLETED)
        stage = {
            "wait_for_user_input": "finance_waiting_for_user",
            "execute_tool": "finance_executing_controlled_operation",
            "request_human_action": "finance_waiting_for_approval",
            "fail_request": "finance_failed",
        }.get(result.next_action.value, "finance_completed")
        return DepartmentExecutionResult(
            department_type=DepartmentType.FINANCE,
            status=status,
            decision=result.decision.value,
            reason=result.reason,
            user_message=result.user_message,
            current_stage=stage,
            completed_step="finance_analysis_completed",
            next_action=result.next_action,
            requires_tool=result.requires_tool,
            tool_request=result.tool_request,
            requires_human_action=result.requires_human_action,
            human_action_request=result.human_action_request,
            is_terminal=result.next_action.value in {"complete_request", "fail_request"},
            safe_event_title=result.safe_event_title,
            safe_event_message=result.safe_event_message,
            state_updates=DepartmentStateUpdates(
                execution=DepartmentExecutionUpdates(
                    last_operation="finance_analysis",
                    last_operation_status=status.value,
                    department_data=result.model_dump(mode="json"),
                ),
                routing=(
                    DepartmentRoutingUpdates(
                        needs_clarification=True,
                        latest_question=result.clarification_question,
                        routing_pending=False,
                    )
                    if result.requires_user_clarification else None
                ),
                human_action=(
                    DepartmentHumanActionUpdates(
                        required=True, request=result.human_action_request
                    )
                    if result.requires_human_action else None
                ),
                result=DepartmentResultUpdates(
                    decision=result.decision.value,
                    reason=result.reason,
                    final_response=result.user_message,
                ),
            ),
        )

    async def persist_result(self, request_id: UUID, result: FinanceDepartmentResult) -> None:
        state = result.state_updates
        completed = result.next_action.value in {"complete_request", "fail_request"}
        await self.finance_requests.upsert(request_id, {
            "requesting_department_id": state.requesting_department_id,
            "budget_id": state.budget_id,
            "category": result.category,
            "requested_amount": result.requested_amount,
            "currency": result.currency,
            "business_reason": state.business_reason or result.reason,
            "cost_center": state.cost_center,
            "available_budget": result.available_budget,
            "budget_sufficient": result.budget_sufficient,
            "policy_compliant": result.policy_compliant,
            "approval_required": result.approval_required,
            "approval_status": state.approval_status,
            "reservation_status": state.reservation_status,
            "decision": result.decision,
            "decision_reason": result.reason,
            "custom_data": {
                "safe_budget_reference": state.safe_budget_reference,
                "clarification_question": result.clarification_question,
            },
            "completed_at": datetime.now(UTC) if completed else None,
        })
