from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.enums import DepartmentType
from app.core.exceptions import NotFoundError
from app.departments.contracts import (
    DepartmentCollaborationRequest,
    DepartmentExecutionContext,
    DepartmentExecutionResult,
    HumanResponseContext,
    ReviewFeedbackContext,
)
from app.departments.exceptions import (
    DepartmentContextMismatchError,
    DepartmentResultValidationError,
    DepartmentStateUpdateError,
)
from app.departments.registry import DepartmentRegistry, build_default_department_registry
from app.departments.customer_support.agent import CustomerSupportDepartmentAgent
from app.departments.customer_support.service import CustomerSupportService
from app.departments.it.agent import ITDepartmentAgent
from app.departments.it.service import ITService
from app.departments.it.schemas import ITDepartmentResult
from app.departments.it.tools import ITToolService
from app.departments.finance.agent import FinanceDepartmentAgent
from app.departments.finance.schemas import FinanceDepartmentResult
from app.departments.finance.service import FinanceService
from app.departments.finance.tools import FinanceBusinessDecisionError, FinanceToolService
from app.departments.procurement.agent import ProcurementDepartmentAgent
from app.departments.procurement.schemas import ProcurementDepartmentResult
from app.departments.procurement.service import ProcurementService
from app.departments.procurement.tools import ProcurementToolService
from app.departments.hr.agent import HRDepartmentAgent
from app.departments.hr.schemas import HRDepartmentResult
from app.departments.hr.service import HRService
from app.departments.hr.tools import HRToolService
from app.users.repository import UserRepository
from app.departments.contracts import DepartmentCollaborationResult
from app.rag.pinecone import PineconeProvider
from app.rag.retrieval import KnowledgeRetrievalService
from app.departments.repository import DepartmentRepository
from app.requests.repository import BusinessRequestRepository
from app.workflow.state import WorkflowState, add_completed_step, apply_state_update


class DepartmentExecutionService:
    """Resolve and execute one trusted tenant department without committing."""

    def __init__(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        *,
        request_repository: BusinessRequestRepository | None = None,
        department_repository: DepartmentRepository | None = None,
        registry: DepartmentRegistry | None = None,
        settings: Settings | None = None,
        pinecone_provider: PineconeProvider | None = None,
        customer_support_service: CustomerSupportService | None = None,
        it_service: ITService | None = None,
        finance_service: FinanceService | None = None,
        procurement_service: ProcurementService | None = None,
        hr_service: HRService | None = None,
        user_repository: UserRepository | None = None,
    ) -> None:
        self.session = session
        self.current_user = current_user
        self.request_repository = request_repository or BusinessRequestRepository(
            session,
            current_user.company_id,
        )
        self.department_repository = department_repository or DepartmentRepository(
            session,
            current_user.company_id,
        )
        self.customer_support_service = customer_support_service
        self.it_service = it_service
        self.finance_service = finance_service
        self.procurement_service = procurement_service
        self.hr_service = hr_service
        self.user_repository = user_repository or UserRepository(session, current_user.company_id)
        if registry is None:
            if customer_support_service is None:
                if settings is None or pinecone_provider is None:
                    raise ValueError("Customer Support settings and Pinecone provider are required")
                customer_support_service = CustomerSupportService(
                    session,
                    current_user,
                    settings,
                    KnowledgeRetrievalService(session, current_user, settings, pinecone_provider),
                )
                self.customer_support_service = customer_support_service
            if it_service is None:
                if settings is None or pinecone_provider is None:
                    raise ValueError("IT settings and Pinecone provider are required")
                it_service = ITService(session, current_user, settings,
                    KnowledgeRetrievalService(session, current_user, settings, pinecone_provider))
                self.it_service = it_service
            if finance_service is None:
                if settings is None or pinecone_provider is None:
                    raise ValueError("Finance settings and Pinecone provider are required")
                finance_service = FinanceService(
                    session,
                    current_user,
                    settings,
                    KnowledgeRetrievalService(
                        session, current_user, settings, pinecone_provider
                    ),
                )
                self.finance_service = finance_service
            if procurement_service is None:
                if settings is None or pinecone_provider is None:
                    raise ValueError("Procurement settings and Pinecone provider are required")
                procurement_service = ProcurementService(
                    session,
                    current_user,
                    settings,
                    KnowledgeRetrievalService(
                        session, current_user, settings, pinecone_provider
                    ),
                )
                self.procurement_service = procurement_service
            if hr_service is None:
                if settings is None or pinecone_provider is None:
                    raise ValueError("HR settings and Pinecone provider are required")
                hr_service = HRService(
                    session,
                    current_user,
                    settings,
                    KnowledgeRetrievalService(
                        session, current_user, settings, pinecone_provider
                    ),
                )
                self.hr_service = hr_service
            registry = build_default_department_registry(
                CustomerSupportDepartmentAgent(customer_support_service),
                ITDepartmentAgent(it_service),
                FinanceDepartmentAgent(finance_service),
                ProcurementDepartmentAgent(procurement_service),
                HRDepartmentAgent(hr_service),
            )
        self.registry = registry

    async def execute(self, state: WorkflowState) -> dict[str, Any]:
        business_request = await self.request_repository.get_by_id(
            state.request.request_id
        )
        if business_request is None:
            raise NotFoundError("Business request not found")
        if (
            business_request.company_id != self.current_user.company_id
            or business_request.company_id != state.request.company_id
            or business_request.requester_user_id != state.request.requester_user_id
        ):
            raise NotFoundError("Business request not found")

        owner_id = business_request.owner_department_id
        active_id = business_request.active_department_id
        if owner_id is None or active_id is None:
            raise DepartmentContextMismatchError(
                "Department execution requires owner and active departments"
            )
        if (
            state.request.owner_department_id != owner_id
            or state.request.active_department_id != active_id
        ):
            raise DepartmentContextMismatchError(
                "Workflow department identity conflicts with the persisted request"
            )

        owner = await self.department_repository.get_by_id(owner_id)
        active = await self.department_repository.get_by_id(active_id)
        if owner is None or active is None:
            raise NotFoundError("Department not found")
        if (
            owner.company_id != self.current_user.company_id
            or active.company_id != self.current_user.company_id
        ):
            raise NotFoundError("Department not found")
        if not owner.is_active or not active.is_active:
            raise DepartmentContextMismatchError("The active department is unavailable")
        if owner.id != active.id or owner.department_type != active.department_type:
            raise DepartmentContextMismatchError(
                "Active and owner departments must match before collaboration is enabled"
            )
        if (
            state.routing.selected_department is not None
            and state.routing.selected_department != owner.department_type
        ):
            raise DepartmentContextMismatchError(
                "The persisted Router result conflicts with the owner department"
            )

        agent = self.registry.resolve(active.department_type)
        requester = await self.user_repository.get_by_id_with_employee(
            business_request.requester_user_id)
        if requester is None or not requester.is_active:
            raise NotFoundError("Requesting user not found")
        context = self._build_context(
            state,
            business_request=business_request,
            owner_department_type=owner.department_type,
            active_department_type=active.department_type,
            requester=requester,
        )
        await self.session.rollback()
        raw_result = await agent.execute(context)
        try:
            result = DepartmentExecutionResult.model_validate(raw_result)
        except ValidationError as exc:
            raise DepartmentResultValidationError(
                "The department returned an invalid structured result"
            ) from exc
        if result.department_type != active.department_type:
            raise DepartmentResultValidationError(
                "The department result does not match the active department"
            )
        return self._safe_state_update(state, result)

    async def execute_it_collaboration(
        self, state: WorkflowState, request: DepartmentCollaborationRequest
    ) -> DepartmentCollaborationResult:
        allowed = {
            (DepartmentType.CUSTOMER_SUPPORT, "diagnose_external_technical_issue"),
            (DepartmentType.HR, "prepare_employee_onboarding_it"),
        }
        if request.request_id != state.request.request_id or request.receiver_department != DepartmentType.IT or (request.sender_department, request.action) not in allowed:
            raise DepartmentContextMismatchError("IT collaboration request is invalid")
        business_request = await self.request_repository.get_by_id(state.request.request_id)
        requester = await self.user_repository.get_by_id_with_employee(state.request.requester_user_id)
        it_department = await self.department_repository.get_by_type(DepartmentType.IT)
        if business_request is None or requester is None or it_department is None or not it_department.is_active:
            raise NotFoundError("IT collaboration context not found")
        context = self._build_context(state, business_request=business_request,
            owner_department_type=request.sender_department,
            active_department_type=DepartmentType.IT, requester=requester).model_copy(
                update={"collaboration_input": request})
        await self.session.rollback()
        raw = await self.registry.resolve(DepartmentType.IT).execute(context)
        result = DepartmentExecutionResult.model_validate(raw)
        if result.department_type != DepartmentType.IT:
            raise DepartmentResultValidationError("IT collaboration returned the wrong department")
        if result.requires_tool or result.requires_collaboration:
            raise DepartmentResultValidationError(
                "IT collaboration cannot start a nested tool or department action"
            )
        data = result.state_updates.execution.department_data if result.state_updates.execution else {}
        return DepartmentCollaborationResult(request_id=request.request_id,
            sender_department=request.sender_department,
            receiver_department=DepartmentType.IT,
            action=request.action,
            status=("unsupported" if result.status.value == "unsupported" else
                "failed" if result.status.value == "failed" else "completed"),
            result={"decision": result.decision, "user_message": result.user_message,
                "requires_human_technician": result.requires_human_action,
                "diagnostic": data or {}}, reason=result.reason)

    async def execute_finance_collaboration(
        self, state: WorkflowState, request: DepartmentCollaborationRequest
    ) -> DepartmentCollaborationResult:
        allowed = {
            (DepartmentType.IT, "validate_it_purchase_budget"),
            (DepartmentType.PROCUREMENT, "validate_procurement_purchase"),
        }
        if (
            request.request_id != state.request.request_id
            or request.receiver_department != DepartmentType.FINANCE
            or (request.sender_department, request.action) not in allowed
        ):
            raise DepartmentContextMismatchError("Finance collaboration request is invalid")
        business_request = await self.request_repository.get_by_id(state.request.request_id)
        requester = await self.user_repository.get_by_id_with_employee(
            state.request.requester_user_id
        )
        finance_department = await self.department_repository.get_by_type(DepartmentType.FINANCE)
        if (
            business_request is None
            or requester is None
            or finance_department is None
            or not finance_department.is_active
            or self.finance_service is None
        ):
            raise NotFoundError("Finance collaboration context not found")
        context = self._build_context(
            state,
            business_request=business_request,
            owner_department_type=request.sender_department,
            active_department_type=DepartmentType.FINANCE,
            requester=requester,
        ).model_copy(update={"collaboration_input": request})
        await self.session.rollback()
        raw = await self.registry.resolve(DepartmentType.FINANCE).execute(context)
        department_result = DepartmentExecutionResult.model_validate(raw)
        if department_result.department_type != DepartmentType.FINANCE:
            raise DepartmentResultValidationError(
                "Finance collaboration returned the wrong department"
            )
        finance_data = (
            department_result.state_updates.execution.department_data
            if department_result.state_updates.execution else {}
        )
        finance_result = FinanceDepartmentResult.model_validate(finance_data)
        tool_result = None
        if department_result.requires_tool:
            if department_result.tool_request is None:
                raise DepartmentResultValidationError("Finance tool request is missing")
            if (
                request.sender_department == DepartmentType.PROCUREMENT
                and department_result.tool_request.operation
                not in {"get_budget_status", "validate_budget_availability"}
            ):
                raise DepartmentResultValidationError(
                    "Procurement collaboration permits read-only Finance validation"
                )
            tool = FinanceToolService(
                self.finance_service.budgets,
                self.finance_service.finance_requests,
                self.finance_service.transactions,
                request_id=state.request.request_id,
                user_id=state.request.requester_user_id,
            )
            try:
                tool_result = await tool.execute(department_result.tool_request)
            except FinanceBusinessDecisionError as exc:
                tool_result = {
                    "operation": department_result.tool_request.operation,
                    "business_decision": "rejected",
                    "reason": str(exc),
                }
        if department_result.requires_collaboration or department_result.requires_review:
            raise DepartmentResultValidationError(
                "Finance collaboration cannot start nested collaboration or review"
            )
        result = {
            "decision": finance_result.decision.value,
            "validated_amount": (
                str(finance_result.requested_amount)
                if finance_result.requested_amount is not None else None
            ),
            "currency": finance_result.currency,
            "budget_reference": finance_result.state_updates.safe_budget_reference,
            "budget_sufficient": finance_result.budget_sufficient,
            "budget_validated": bool(
                finance_result.budget_sufficient
                and finance_result.policy_compliant
                and not finance_result.approval_required
                and not (tool_result and tool_result.get("business_decision") == "rejected")
            ),
            "approval_required": finance_result.approval_required,
            "reservation_result": tool_result,
            "required_next_action": finance_result.next_action.value,
            "finance_data": finance_result.model_dump(mode="json"),
        }
        return DepartmentCollaborationResult(
            request_id=request.request_id,
            sender_department=DepartmentType.FINANCE,
            receiver_department=request.sender_department,
            action=request.action,
            status=(
                "unsupported" if department_result.status.value == "unsupported"
                else "failed" if department_result.status.value == "failed"
                else "completed"
            ),
            result=result,
            reason=department_result.reason,
        )

    async def execute_it_tool(self, state: WorkflowState) -> dict[str, Any]:
        result = DepartmentExecutionResult.model_validate(state.execution.department_result)
        if result.department_type != DepartmentType.IT or result.tool_request is None:
            raise DepartmentContextMismatchError("Only validated IT tools are active")
        operation = result.tool_request.operation
        if any(item.get("operation") == operation for item in state.execution.tool_results):
            raise DepartmentStateUpdateError("The IT read tool already completed")
        if self.it_service is None:
            raise DepartmentContextMismatchError("IT service is unavailable")
        tool = ITToolService(self.it_service.assets, self.it_service.software)
        try:
            output = await tool.execute(result.tool_request)
        except FinanceBusinessDecisionError as exc:
            output = {
                "operation": result.tool_request.operation,
                "business_decision": "rejected",
                "reason": str(exc),
            }
        await self.session.rollback()
        return output

    async def execute_finance_tool(self, state: WorkflowState) -> dict[str, Any]:
        result = DepartmentExecutionResult.model_validate(state.execution.department_result)
        if result.department_type != DepartmentType.FINANCE or result.tool_request is None:
            raise DepartmentContextMismatchError("Only validated Finance tools are active")
        reference = result.tool_request.idempotency_key
        if any(
            item.get("operation") == result.tool_request.operation
            and (reference is None or item.get("idempotency_reference") == reference)
            for item in state.execution.tool_results
        ):
            raise DepartmentStateUpdateError("The Finance tool already completed")
        if self.finance_service is None:
            raise DepartmentContextMismatchError("Finance service is unavailable")
        tool = FinanceToolService(
            self.finance_service.budgets,
            self.finance_service.finance_requests,
            self.finance_service.transactions,
            request_id=state.request.request_id,
            user_id=state.request.requester_user_id,
        )
        output = await tool.execute(result.tool_request)
        if reference is not None:
            output["idempotency_reference"] = reference
        return output

    async def execute_procurement_tool(self, state: WorkflowState) -> dict[str, Any]:
        result = DepartmentExecutionResult.model_validate(
            state.execution.department_result
        )
        if (
            result.department_type != DepartmentType.PROCUREMENT
            or result.tool_request is None
        ):
            raise DepartmentContextMismatchError(
                "Only validated Procurement tools are active"
            )
        operation = result.tool_request.operation
        if any(item.get("operation") == operation for item in state.execution.tool_results):
            raise DepartmentStateUpdateError(
                "The Procurement tool operation already completed"
            )
        if self.procurement_service is None:
            raise DepartmentContextMismatchError("Procurement service is unavailable")
        tool = ProcurementToolService(
            self.procurement_service.candidates,
            request_id=state.request.request_id,
        )
        return await tool.execute(result.tool_request)

    async def execute_hr_tool(self, state: WorkflowState) -> dict[str, Any]:
        result = DepartmentExecutionResult.model_validate(state.execution.department_result)
        if result.department_type != DepartmentType.HR or result.tool_request is None:
            raise DepartmentContextMismatchError("Only validated HR tools are active")
        if self.hr_service is None:
            raise DepartmentContextMismatchError("HR service is unavailable")
        operation = result.tool_request.operation
        if any(item.get("operation") == operation for item in state.execution.tool_results):
            raise DepartmentStateUpdateError("The HR tool operation already completed")
        tool = HRToolService(
            self.hr_service.balances, self.hr_service.leave_requests,
            self.hr_service.holidays, self.hr_service.onboarding,
            self.hr_service.job_descriptions, request_id=state.request.request_id,
        )
        return await tool.execute(result.tool_request)

    async def execute_procurement_collaboration(
        self, state: WorkflowState, request: DepartmentCollaborationRequest
    ) -> DepartmentCollaborationResult:
        if (
            request.request_id != state.request.request_id
            or request.sender_department != DepartmentType.IT
            or request.receiver_department != DepartmentType.PROCUREMENT
            or request.action != "find_it_asset_suppliers"
        ):
            raise DepartmentContextMismatchError(
                "Procurement collaboration request is invalid"
            )
        business_request = await self.request_repository.get_by_id(
            state.request.request_id
        )
        requester = await self.user_repository.get_by_id_with_employee(
            state.request.requester_user_id
        )
        department = await self.department_repository.get_by_type(
            DepartmentType.PROCUREMENT
        )
        if (
            business_request is None
            or requester is None
            or department is None
            or not department.is_active
            or self.procurement_service is None
        ):
            raise NotFoundError("Procurement collaboration context not found")
        context = self._build_context(
            state,
            business_request=business_request,
            owner_department_type=DepartmentType.IT,
            active_department_type=DepartmentType.PROCUREMENT,
            requester=requester,
        ).model_copy(update={"collaboration_input": request})
        await self.session.rollback()
        department_result = DepartmentExecutionResult.model_validate(
            await self.registry.resolve(DepartmentType.PROCUREMENT).execute(context)
        )
        if department_result.department_type != DepartmentType.PROCUREMENT:
            raise DepartmentResultValidationError(
                "Procurement collaboration returned the wrong department"
            )

        tool_results = list(context.tool_results)
        if department_result.requires_tool:
            if department_result.tool_request is None:
                raise DepartmentResultValidationError(
                    "Procurement collaboration tool request is missing"
                )
            tool = ProcurementToolService(
                self.procurement_service.candidates,
                request_id=state.request.request_id,
            )
            tool_results.append(await tool.execute(department_result.tool_request))
            await self.session.rollback()
            context = context.model_copy(update={"tool_results": tool_results})
            department_result = DepartmentExecutionResult.model_validate(
                await self.registry.resolve(DepartmentType.PROCUREMENT).execute(context)
            )

        finance_data = None
        if department_result.requires_collaboration:
            finance_request = department_result.collaboration_request
            if finance_request is None:
                raise DepartmentResultValidationError(
                    "Procurement Finance collaboration request is missing"
                )
            finance_result = await self.execute_finance_collaboration(
                state, finance_request
            )
            finance_data = finance_result.result.get("finance_data")
            await self.session.rollback()
            context = context.model_copy(
                update={
                    "collaboration_result": finance_result,
                    "tool_results": tool_results,
                }
            )
            department_result = DepartmentExecutionResult.model_validate(
                await self.registry.resolve(DepartmentType.PROCUREMENT).execute(context)
            )
        if department_result.requires_tool or department_result.requires_collaboration:
            raise DepartmentResultValidationError(
                "Procurement collaboration did not reach a stable outcome"
            )
        data = (
            department_result.state_updates.execution.department_data
            if department_result.state_updates.execution
            else {}
        )
        return DepartmentCollaborationResult(
            request_id=request.request_id,
            sender_department=DepartmentType.PROCUREMENT,
            receiver_department=DepartmentType.IT,
            action=request.action,
            status=(
                "unsupported"
                if department_result.status.value == "unsupported"
                else "failed"
                if department_result.status.value == "failed"
                else "completed"
            ),
            result={
                "decision": department_result.decision,
                "user_message": department_result.user_message,
                "procurement_data": data or {},
                "finance_data": finance_data,
            },
            reason=department_result.reason,
        )

    async def persist_it_collaboration_result(self, state: WorkflowState) -> None:
        if self.it_service is None or not state.collaboration.structured_result:
            return
        collaboration = DepartmentCollaborationResult.model_validate(state.collaboration.structured_result)
        if collaboration.receiver_department != DepartmentType.IT:
            return
        diagnostic = collaboration.result.get("diagnostic")
        if diagnostic:
            await self.it_service.persist_result(state.request.request_id,
                ITDepartmentResult.model_validate(diagnostic),
                reported_by_user_id=state.request.requester_user_id)

    async def persist_finance_collaboration_result(self, state: WorkflowState) -> None:
        if self.finance_service is None or not state.collaboration.structured_result:
            return
        collaboration = DepartmentCollaborationResult.model_validate(
            state.collaboration.structured_result
        )
        if collaboration.sender_department != DepartmentType.FINANCE:
            return
        data = collaboration.result.get("finance_data")
        if data:
            await self.finance_service.persist_result(
                state.request.request_id,
                FinanceDepartmentResult.model_validate(data),
            )

    async def persist_procurement_collaboration_result(
        self, state: WorkflowState
    ) -> None:
        if self.procurement_service is None or not state.collaboration.structured_result:
            return
        collaboration = DepartmentCollaborationResult.model_validate(
            state.collaboration.structured_result
        )
        if collaboration.sender_department != DepartmentType.PROCUREMENT:
            return
        data = collaboration.result.get("procurement_data")
        if data:
            await self.procurement_service.persist_result(
                state.request.request_id,
                ProcurementDepartmentResult.model_validate(data),
            )
        finance_data = collaboration.result.get("finance_data")
        if finance_data and self.finance_service is not None:
            await self.finance_service.persist_result(
                state.request.request_id,
                FinanceDepartmentResult.model_validate(finance_data),
            )

    async def persist_department_result(self, state: WorkflowState) -> None:
        raw = state.execution.department_result
        if not raw:
            return
        data = raw.get("state_updates", {}).get("execution", {}).get("department_data")
        if data and raw.get("department_type") == DepartmentType.CUSTOMER_SUPPORT.value and self.customer_support_service:
            from app.departments.customer_support.schemas import CustomerSupportResult
            await self.customer_support_service.persist_result(
                state.request.request_id,
                CustomerSupportResult.model_validate(data),
            )
        if data and raw.get("department_type") == DepartmentType.IT.value and self.it_service:
            await self.it_service.persist_result(state.request.request_id,
                ITDepartmentResult.model_validate(data),
                reported_by_user_id=state.request.requester_user_id)
        if (
            data
            and raw.get("department_type") == DepartmentType.FINANCE.value
            and self.finance_service
        ):
            await self.finance_service.persist_result(
                state.request.request_id,
                FinanceDepartmentResult.model_validate(data),
            )
        if (
            data
            and raw.get("department_type") == DepartmentType.PROCUREMENT.value
            and self.procurement_service
        ):
            await self.procurement_service.persist_result(
                state.request.request_id,
                ProcurementDepartmentResult.model_validate(data),
            )
        if data and raw.get("department_type") == DepartmentType.HR.value and self.hr_service:
            await self.hr_service.persist_result(
                state.request.request_id,
                HRDepartmentResult.model_validate(data),
            )

    @staticmethod
    def _build_context(
        state: WorkflowState,
        *,
        business_request: Any,
        owner_department_type: DepartmentType,
        active_department_type: DepartmentType,
        requester: Any,
    ) -> DepartmentExecutionContext:
        collaboration_input = None
        if state.collaboration.request:
            collaboration_input = DepartmentCollaborationRequest.model_validate(
                state.collaboration.request
            )
        collaboration_result = None
        if state.collaboration.structured_result:
            collaboration_result = DepartmentCollaborationResult.model_validate(
                state.collaboration.structured_result)
        review_feedback = None
        if state.review.feedback:
            review_feedback = ReviewFeedbackContext.model_validate(
                state.review.feedback
            )
        human_response = None
        if state.human_action.response:
            human_response = HumanResponseContext.model_validate(
                state.human_action.response
            )
        return DepartmentExecutionContext(
            request_id=state.request.request_id,
            company_id=state.request.company_id,
            requester_user_id=state.request.requester_user_id,
            requester_employee_id=state.request.requester_employee_id,
            requester_department_id=(requester.employee.department_id if requester.employee else None),
            requester_actor_type=requester.actor_type,
            requester_is_manager=requester.actor_type.value == "department_manager",
            owner_department_type=owner_department_type,
            active_department_type=active_department_type,
            request_type=state.request.request_type,
            request_summary=state.request.summary,
            current_stage=state.request.current_stage,
            current_plan=state.planning.current_plan,
            completed_steps=state.planning.completed_steps,
            pending_steps=state.planning.pending_steps,
            relevant_custom_data=business_request.custom_data,
            latest_user_input=state.routing.latest_answer,
            collaboration_input=collaboration_input,
            collaboration_result=collaboration_result,
            review_feedback=review_feedback,
            human_response=human_response,
            tool_results=state.execution.tool_results,
            department_data=state.execution.department_data,
        )

    @staticmethod
    def _safe_state_update(
        state: WorkflowState,
        result: DepartmentExecutionResult,
    ) -> dict[str, Any]:
        updates = result.state_updates
        if updates.current_stage is not None and updates.current_stage != result.current_stage:
            raise DepartmentStateUpdateError(
                "Conflicting department current-stage updates are prohibited"
            )

        request = state.request.model_copy(
            update={"current_stage": result.current_stage}
        )
        planning = add_completed_step(state, result.completed_step)
        if updates.planning is not None:
            planning_values = updates.planning.model_dump(exclude_none=True)
            planning = planning.model_copy(update=planning_values)
        if len(planning.completed_steps) != len(set(planning.completed_steps)):
            raise DepartmentStateUpdateError("Completed workflow steps must be unique")
        if set(planning.completed_steps).intersection(planning.pending_steps):
            raise DepartmentStateUpdateError(
                "A completed workflow step cannot remain pending"
            )

        execution = state.execution
        if updates.execution is not None:
            execution = execution.model_copy(
                update=updates.execution.model_dump(exclude_none=True)
            )
        execution = execution.model_copy(
            update={"department_result": result.model_dump(mode="json")}
        )

        routing = state.routing
        if updates.routing is not None:
            routing = routing.model_copy(update=updates.routing.model_dump(exclude_none=True))

        collaboration = state.collaboration
        if updates.collaboration is not None:
            collaboration = collaboration.model_copy(
                update={
                    "request": (
                        updates.collaboration.request.model_dump(mode="json")
                        if updates.collaboration.request is not None
                        else {}
                    ),
                    "structured_result": (
                        updates.collaboration.result.model_dump(mode="json")
                        if updates.collaboration.result is not None
                        else {}
                    ),
                    "is_active": updates.collaboration.is_active,
                }
            )

        review = state.review
        if updates.review is not None:
            review_values = updates.review.model_dump(
                mode="json",
                exclude_none=True,
            )
            review = review.model_copy(update=review_values)

        human_action = state.human_action
        if updates.human_action is not None:
            human_values = updates.human_action.model_dump(
                mode="json",
                exclude_none=True,
            )
            human_action = human_action.model_copy(update=human_values)

        result_state = state.result
        if updates.result is not None:
            result_state = result_state.model_copy(
                update=updates.result.model_dump(exclude_none=True)
            )
        if result.next_action.value == "complete_request":
            result_state = result_state.model_copy(
                update={
                    "decision": result.decision,
                    "reason": result.reason,
                    "final_response": result.user_message,
                }
            )

        merged = apply_state_update(
            state,
            {
                "request": request,
                "planning": planning,
                "execution": execution,
                "routing": routing,
                "collaboration": collaboration,
                "review": review,
                "human_action": human_action,
                "result": result_state,
            },
        )
        return {
            "request": merged.request,
            "planning": merged.planning,
            "execution": merged.execution,
            "routing": merged.routing,
            "collaboration": merged.collaboration,
            "review": merged.review,
            "human_action": merged.human_action,
            "result": merged.result,
        }
