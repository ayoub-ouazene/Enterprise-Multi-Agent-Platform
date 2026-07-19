from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.companies.repository import CompanyRepository
from app.core.config import Settings
from app.core.enums import ActorType, DepartmentType, EmploymentStatus
from app.departments.contracts import (
    DepartmentCollaborationUpdates,
    DepartmentExecutionContext,
    DepartmentExecutionResult,
    DepartmentExecutionStatus,
    DepartmentExecutionUpdates,
    DepartmentHumanActionRequest,
    DepartmentHumanActionUpdates,
    DepartmentNextAction,
    DepartmentResultUpdates,
    DepartmentRoutingUpdates,
    DepartmentStateUpdates,
)
from app.departments.customer_support.service import requester_access_scopes
from app.departments.hr.calculations import (
    HRBusinessDecisionError,
    calculate_workdays,
    staffing_satisfied,
)
from app.departments.hr.enums import (
    ApprovalStatus,
    BalanceStatus,
    EligibilityStatus,
    HRDecision,
    HRModelRole,
    HRRequestCategory,
    JobDescriptionStatus,
    LeaveDecision,
    OnboardingStatus,
    StaffingStatus,
)
from app.departments.hr.model_policy import initial_model_role, requires_reasoning_pass
from app.departments.hr.repository import (
    CompanyHolidayRepository,
    DepartmentStaffingRuleRepository,
    JobDescriptionRepository,
    LeaveBalanceRepository,
    LeaveRequestRepository,
    OnboardingRequestRepository,
)
from app.departments.hr.schemas import HRDepartmentResult, HRExecutionInput
from app.employees.repository import EmployeeRepository
from app.llm.groq import GroqHRClient
from app.rag.enums import KnowledgeDepartmentScope
from app.rag.retrieval import KnowledgeRetrievalService
from app.rag.schemas import KnowledgeRetrievalQuery


class HRService:
    def __init__(
        self,
        session: AsyncSession,
        requester: AuthenticatedUser,
        settings: Settings,
        retrieval: KnowledgeRetrievalService,
        *,
        llm_client: Any | None = None,
        employee_repository: EmployeeRepository | None = None,
        balance_repository: LeaveBalanceRepository | None = None,
        leave_repository: LeaveRequestRepository | None = None,
        holiday_repository: CompanyHolidayRepository | None = None,
        staffing_repository: DepartmentStaffingRuleRepository | None = None,
        onboarding_repository: OnboardingRequestRepository | None = None,
        job_description_repository: JobDescriptionRepository | None = None,
    ) -> None:
        self.session, self.requester, self.settings, self.retrieval = session, requester, settings, retrieval
        company_id = requester.company_id
        self.llm = llm_client or GroqHRClient(settings)
        self.employees = employee_repository or EmployeeRepository(session, company_id)
        self.balances = balance_repository or LeaveBalanceRepository(session, company_id)
        self.leave_requests = leave_repository or LeaveRequestRepository(session, company_id)
        self.holidays = holiday_repository or CompanyHolidayRepository(session, company_id)
        self.staffing = staffing_repository or DepartmentStaffingRuleRepository(session, company_id)
        self.onboarding = onboarding_repository or OnboardingRequestRepository(session, company_id)
        self.job_descriptions = job_description_repository or JobDescriptionRepository(session, company_id)

    async def execute(self, context: DepartmentExecutionContext) -> DepartmentExecutionResult:
        model_input = await self._build_input(context)
        await self.session.rollback()
        evidence = await self.retrieval.search_trusted(KnowledgeRetrievalQuery(
            company_id=context.company_id,
            query_text=self._query(context),
            departments=[KnowledgeDepartmentScope.HR, KnowledgeDepartmentScope.SHARED],
            allowed_access_scopes=requester_access_scopes(AuthenticatedUser(
                user_id=context.requester_user_id, company_id=context.company_id,
                email="trusted-requester@internal.invalid", actor_type=context.requester_actor_type,
                employee_id=context.requester_employee_id, department_id=context.requester_department_id,
                is_manager=context.requester_is_manager,
            )),
            top_k=self.settings.rag_top_k,
        ))
        await self.session.rollback()
        model_input = model_input.model_copy(update={"evidence": [self._evidence(item) for item in evidence]})
        role = initial_model_role(model_input)
        result = await self.llm.generate(model_input, role=role)
        if requires_reasoning_pass(result, role):
            result = await self.llm.generate(model_input, role=HRModelRole.REASONING)
        result = await self._apply_authoritative_facts(result, context)
        result = HRDepartmentResult.model_validate(result.model_dump(mode="json"))
        self._validate(result, evidence, model_input)
        await self.session.rollback()
        return self._to_department_result(result)

    async def _build_input(self, context: DepartmentExecutionContext) -> HRExecutionInput:
        target_id = context.requester_employee_id
        trusted_target = context.relevant_custom_data.get("employee_id")
        if trusted_target and context.requester_actor_type in {ActorType.COMPANY, ActorType.DEPARTMENT_MANAGER}:
            try:
                target_id = UUID(str(trusted_target))
            except ValueError:
                target_id = None
        employee = await self.employees.get_by_id(target_id) if target_id else None
        balances = await self.balances.list_for_employee(employee.id) if employee else []
        existing_leave = await self.leave_requests.get(context.request_id)
        existing_onboarding = await self.onboarding.get(context.request_id)
        company = await CompanyRepository(self.session).get_by_id(context.company_id)
        employee_data = {}
        benefits = {}
        if employee:
            employee_data = {
                "employee_id": str(employee.id),
                "department_id": str(employee.department_id) if employee.department_id else None,
                "manager_employee_id": str(employee.manager_employee_id) if employee.manager_employee_id else None,
                "employment_status": employee.employment_status.value,
                "hire_date": employee.hire_date.isoformat() if employee.hire_date else None,
                "job_title": employee.job_title,
            }
            raw_employee_benefits = employee.custom_data.get("benefits", {})
            if isinstance(raw_employee_benefits, dict):
                benefits["employee"] = raw_employee_benefits
        if company:
            raw_company_benefits = company.custom_data.get("benefits", {})
            if isinstance(raw_company_benefits, dict):
                benefits["company"] = raw_company_benefits
        return HRExecutionInput(
            request_id=context.request_id, company_id=context.company_id,
            requester_user_id=context.requester_user_id, requester_employee_id=context.requester_employee_id,
            requester_department_id=context.requester_department_id, requester_actor_type=context.requester_actor_type,
            requester_is_manager=context.requester_is_manager,
            owner_department_type=context.owner_department_type, active_department_type=context.active_department_type,
            request_type=context.request_type, original_summary=context.request_summary,
            latest_user_input=context.latest_user_input, current_stage=context.current_stage,
            employee_data=employee_data,
            leave_balances=[{"leave_type": item.leave_type.value, "year": item.year,
                "allocated_days": str(item.allocated_days), "used_days": str(item.used_days),
                "reserved_days": str(item.reserved_days), "remaining_days": str(item.remaining_days)} for item in balances],
            leave_request=self._leave_data(existing_leave),
            benefits_eligibility=benefits,
            onboarding_state=self._onboarding_data(existing_onboarding),
            collaboration_input=context.collaboration_input,
            collaboration_result=context.collaboration_result,
            human_response=context.human_response.model_dump(mode="json") if context.human_response else {},
            tool_results=context.tool_results,
            previous_hr_state=context.department_data,
        )

    async def _apply_authoritative_facts(self, result: HRDepartmentResult, context: DepartmentExecutionContext) -> HRDepartmentResult:
        if result.category not in {HRRequestCategory.LEAVE_REQUEST, HRRequestCategory.VACATION_REQUEST}:
            return result
        state = result.state_updates
        employee_id = state.employee_id or context.requester_employee_id
        if employee_id is None or state.leave_type is None or state.start_date is None or state.end_date is None:
            return result
        employee = await self.employees.get_by_id(employee_id)
        if employee is None or employee.employment_status != EmploymentStatus.ACTIVE:
            return result.model_copy(update={"leave_eligible": False, "decision": HRDecision.REJECTED,
                "reason": "An active employee record is required.", "user_message": "This leave request cannot be processed from the available employee record.",
                "approval_required": False, "requires_tool": False, "tool_request": None,
                "requires_human_action": False, "human_action_request": None,
                "requires_it_collaboration": False, "it_collaboration_request": None,
                "next_action": DepartmentNextAction.COMPLETE_REQUEST,
                "state_updates": state.model_copy(update={"employee_id": employee.id if employee else None, "eligibility_status": EligibilityStatus.INELIGIBLE,
                    "leave_decision": LeaveDecision.REJECTED})})
        holidays = await self.holidays.dates_between(state.start_date, state.end_date)
        try:
            requested = calculate_workdays(state.start_date, state.end_date, holidays)
        except HRBusinessDecisionError as exc:
            return result.model_copy(update={"leave_eligible": False, "decision": HRDecision.REJECTED,
                    "reason": str(exc), "user_message": str(exc), "approval_required": False,
                    "requires_tool": False, "tool_request": None,
                    "requires_human_action": False, "human_action_request": None,
                    "requires_it_collaboration": False, "it_collaboration_request": None,
                    "next_action": DepartmentNextAction.COMPLETE_REQUEST,
                "state_updates": state.model_copy(update={"employee_id": employee_id,
                    "eligibility_status": EligibilityStatus.INELIGIBLE, "leave_decision": LeaveDecision.REJECTED})})
        balance = await self.balances.get_for_employee(employee_id, state.leave_type, state.start_date.year)
        sufficient = balance is not None and balance.remaining_days >= requested
        policy = balance.custom_data if balance else {}
        type_enabled = bool(balance and policy.get("enabled", True))
        eligible = type_enabled
        staffing_status = StaffingStatus.NOT_APPLICABLE
        staffing_ok: bool | None = None
        rule = None
        if employee.department_id:
            rule = await self.staffing.applicable(employee.department_id, state.start_date, state.end_date)
        if rule and employee.department_id:
            ids = await self.employees.active_ids_in_department(employee.department_id)
            overlap = await self.leave_requests.overlapping_count(ids, state.start_date, state.end_date, exclude_request_id=context.request_id)
            staffing_ok = staffing_satisfied(active_employees=len(ids), overlapping_absences=overlap, minimum_active=rule.minimum_active_employees)
            staffing_status = StaffingStatus.SATISFIED if staffing_ok else StaffingStatus.CONFLICT
        auto_enabled = bool(policy.get("auto_approval_enabled", False))
        max_days = Decimal(str(policy.get("auto_approval_max_days", "0")))
        approval_required = not (auto_enabled and max_days > 0 and requested <= max_days and staffing_ok is True)
        human_decision = str(context.human_response.decision).casefold() if context.human_response else ""
        approved_by_human = human_decision in {"approved", "approve"}
        rejected_by_human = human_decision in {"rejected", "reject"}
        if not eligible or not sufficient or staffing_ok is False:
            approval_required = False
            decision = HRDecision.REJECTED
            leave_decision = LeaveDecision.REJECTED
            approval_status = ApprovalStatus.NOT_REQUIRED
            next_action = DepartmentNextAction.COMPLETE_REQUEST
            safe_reason = "The employee or leave type is not eligible under the available policy." if not eligible else (
                "The available leave balance is insufficient." if not sufficient else "The requested dates conflict with minimum staffing requirements."
            )
        elif rejected_by_human:
            decision = HRDecision.REJECTED
            leave_decision = LeaveDecision.REJECTED
            approval_status = ApprovalStatus.REJECTED
            next_action = DepartmentNextAction.COMPLETE_REQUEST
            safe_reason = "The authorized manager rejected the leave request."
        elif approval_required and not approved_by_human:
            decision = HRDecision.PENDING_APPROVAL
            leave_decision = LeaveDecision.PENDING
            approval_status = ApprovalStatus.PENDING
            next_action = DepartmentNextAction.REQUEST_HUMAN_ACTION
            safe_reason = "The leave request passed deterministic checks and requires manager approval."
        else:
            decision = HRDecision.APPROVED
            leave_decision = LeaveDecision.APPROVED
            approval_status = ApprovalStatus.APPROVED if approved_by_human else ApprovalStatus.NOT_REQUIRED
            next_action = DepartmentNextAction.COMPLETE_REQUEST
            safe_reason = "The leave request passed deterministic eligibility, balance, and staffing checks."
        updated_state = state.model_copy(update={
            "employee_id": employee_id, "requested_days": requested,
            "eligibility_status": EligibilityStatus.ELIGIBLE if eligible else EligibilityStatus.INELIGIBLE,
            "balance_status": BalanceStatus.SUFFICIENT if sufficient else BalanceStatus.INSUFFICIENT,
            "staffing_status": staffing_status, "approval_status": approval_status,
            "leave_decision": leave_decision,
            "reserved_days": requested if leave_decision == LeaveDecision.APPROVED else Decimal("0.00"),
        })
        human_request = None
        if next_action == DepartmentNextAction.REQUEST_HUMAN_ACTION:
            human_request = result.human_action_request or DepartmentHumanActionRequest(
                action_type="approve_leave_request",
                assigned_role=ActorType.DEPARTMENT_MANAGER,
                request_summary=f"Leave request for {requested} workdays from {state.start_date} to {state.end_date}.",
                evidence_summary=f"Balance sufficient: {sufficient}; staffing satisfied: {staffing_ok}.",
                recommendation="Approve only after confirming managerial responsibility and the supplied policy references.",
                exact_action_required="Approve or reject this leave request.",
                reason=safe_reason,
            )
        return result.model_copy(update={
            "decision": decision, "leave_eligible": eligible,
            "leave_balance_sufficient": sufficient, "minimum_staffing_satisfied": staffing_ok,
            "approval_required": approval_required,
            "reason": safe_reason, "user_message": safe_reason,
            "needs_user_clarification": False, "clarification_question": None,
            "requires_tool": False, "tool_request": None,
            "requires_it_collaboration": False, "it_collaboration_request": None,
            "requires_human_action": next_action == DepartmentNextAction.REQUEST_HUMAN_ACTION,
            "human_action_request": human_request,
            "next_action": next_action, "state_updates": updated_state,
        })

    @staticmethod
    def _validate(result: HRDepartmentResult, evidence: list[Any], context: HRExecutionInput) -> None:
        allowed = {(item.document_id, item.title, item.document_type, item.version, item.chunk_index) for item in evidence}
        if any((source.document_id, source.title, source.document_type, source.version, source.chunk_index) not in allowed for source in result.sources_used):
            raise ValueError("HR returned an unauthorized source reference")
        if result.clarification_question and result.clarification_question == context.previous_hr_state.get("clarification_question"):
            raise ValueError("HR repeated a clarification question")
        if result.category == HRRequestCategory.HR_INFORMATION and result.decision == HRDecision.INFORMATION_PROVIDED and not result.sources_used:
            raise ValueError("HR informational answers require authorized evidence")
        if result.category == HRRequestCategory.BENEFITS_INFORMATION and result.benefits_answer and not context.benefits_eligibility and not result.sources_used:
            raise ValueError("Benefits answer is not grounded")
        trusted_employee = context.employee_data.get("employee_id")
        if result.state_updates.employee_id is not None and str(result.state_updates.employee_id) != trusted_employee:
            raise ValueError("HR attempted to substitute the trusted employee")
        collaboration = result.it_collaboration_request
        if collaboration is not None and (
            collaboration.request_id != context.request_id
            or collaboration.sender_department != DepartmentType.HR
            or collaboration.receiver_department != DepartmentType.IT
            or collaboration.action != "prepare_employee_onboarding_it"
            or str(collaboration.payload.get("employee_id")) != trusted_employee
        ):
            raise ValueError("HR IT collaboration is outside the authorized boundary")

    @staticmethod
    def _to_department_result(result: HRDepartmentResult) -> DepartmentExecutionResult:
        status = {
            "wait_for_user_input": DepartmentExecutionStatus.WAITING_FOR_USER,
            "execute_tool": DepartmentExecutionStatus.WAITING_FOR_TOOL,
            "collaborate": DepartmentExecutionStatus.WAITING_FOR_DEPARTMENT,
            "request_human_action": DepartmentExecutionStatus.WAITING_FOR_HUMAN,
            "fail_request": DepartmentExecutionStatus.UNSUPPORTED,
        }.get(result.next_action.value, DepartmentExecutionStatus.COMPLETED)
        stage = {
            "wait_for_user_input": "hr_waiting_for_user", "execute_tool": "hr_running_controlled_check",
            "collaborate": "hr_waiting_for_it", "request_human_action": "hr_waiting_for_manager_approval",
            "fail_request": "hr_failed",
        }.get(result.next_action.value, "hr_completed")
        return DepartmentExecutionResult(
            department_type=DepartmentType.HR, status=status, decision=result.decision.value,
            reason=result.reason, user_message=result.user_message, current_stage=stage,
            completed_step="hr_analysis_completed", next_action=result.next_action,
            next_department=DepartmentType.IT if result.requires_it_collaboration else None,
            requires_tool=result.requires_tool, tool_request=result.tool_request,
            requires_collaboration=result.requires_it_collaboration,
            collaboration_request=result.it_collaboration_request,
            requires_human_action=result.requires_human_action,
            human_action_request=result.human_action_request,
            is_terminal=result.next_action.value in {"complete_request", "fail_request"},
            safe_event_title=result.safe_event_title, safe_event_message=result.safe_event_message,
            state_updates=DepartmentStateUpdates(
                execution=DepartmentExecutionUpdates(last_operation="hr_analysis", last_operation_status=status.value,
                    department_data=result.model_dump(mode="json")),
                routing=DepartmentRoutingUpdates(needs_clarification=True, latest_question=result.clarification_question,
                    routing_pending=False) if result.needs_user_clarification else None,
                collaboration=DepartmentCollaborationUpdates(request=result.it_collaboration_request, is_active=True) if result.requires_it_collaboration else None,
                human_action=DepartmentHumanActionUpdates(required=True, request=result.human_action_request) if result.requires_human_action else None,
                result=DepartmentResultUpdates(decision=result.decision.value, reason=result.reason, final_response=result.user_message),
            ),
        )

    async def persist_result(self, request_id: UUID, result: HRDepartmentResult) -> None:
        state = result.state_updates
        if result.category in {HRRequestCategory.LEAVE_REQUEST, HRRequestCategory.VACATION_REQUEST}:
            if state.employee_id is None or state.requested_days is None:
                return
            await self._persist_leave(request_id, result)
        elif result.category == HRRequestCategory.ONBOARDING and state.employee_id and state.onboarding_start_date and state.onboarding_department_id:
            await self.onboarding.upsert(request_id, {
                "employee_id": state.employee_id, "start_date": state.onboarding_start_date,
                "department_id": state.onboarding_department_id,
                "manager_employee_id": state.onboarding_manager_employee_id,
                "onboarding_status": state.onboarding_status or OnboardingStatus.PREPARING,
                "required_actions": state.onboarding_actions,
                "completed_actions": state.completed_onboarding_actions,
                "missing_data": state.onboarding_missing_data, "custom_data": {},
                "completed_at": datetime.now(UTC) if state.onboarding_status == OnboardingStatus.COMPLETED else None,
            })
        elif result.category == HRRequestCategory.JOB_DESCRIPTION and state.job_description:
            draft = state.job_description
            await self.job_descriptions.upsert_for_request(request_id, {
                **draft.model_dump(exclude={"status"}), "status": JobDescriptionStatus.DRAFT,
                "created_by_user_id": self.requester.user_id, "custom_data": {},
            })

    async def _persist_leave(self, request_id: UUID, result: HRDepartmentResult) -> None:
        state = result.state_updates
        if not all((state.employee_id, state.leave_type, state.start_date, state.end_date, state.requested_days)):
            raise HRBusinessDecisionError("Leave request fields are incomplete")
        existing = await self.leave_requests.get(request_id, for_update=True)
        balance = await self.balances.get_for_employee(state.employee_id, state.leave_type, state.start_date.year, for_update=True)
        holidays = await self.holidays.dates_between(state.start_date, state.end_date)
        requested = calculate_workdays(state.start_date, state.end_date, holidays)
        if requested != state.requested_days:
            raise HRBusinessDecisionError("Leave calculation changed before persistence")
        old_reserved = existing.reserved_days if existing else Decimal("0.00")
        desired_reserved = requested if state.leave_decision == LeaveDecision.APPROVED else Decimal("0.00")
        if desired_reserved > old_reserved:
            if balance is None or balance.remaining_days < desired_reserved - old_reserved:
                raise HRBusinessDecisionError("Leave balance became insufficient")
            if state.staffing_status != StaffingStatus.SATISFIED:
                raise HRBusinessDecisionError("Staffing no longer permits approval")
            employee = await self.employees.get_by_id(state.employee_id, for_update=True)
            if employee is None or employee.department_id is None:
                raise HRBusinessDecisionError("Employee staffing context is unavailable")
            rule = await self.staffing.applicable(employee.department_id, state.start_date, state.end_date, for_update=True)
            if rule is None:
                raise HRBusinessDecisionError("Staffing policy is unavailable")
            ids = await self.employees.active_ids_in_department(employee.department_id)
            overlaps = await self.leave_requests.overlapping_count(ids, state.start_date, state.end_date, exclude_request_id=request_id)
            if not staffing_satisfied(active_employees=len(ids), overlapping_absences=overlaps, minimum_active=rule.minimum_active_employees):
                raise HRBusinessDecisionError("Staffing availability changed before approval")
            balance.reserved_days += desired_reserved - old_reserved
        elif desired_reserved < old_reserved:
            if balance is None or balance.reserved_days < old_reserved - desired_reserved:
                raise HRBusinessDecisionError("Leave reservation state is inconsistent")
            balance.reserved_days -= old_reserved - desired_reserved
        await self.leave_requests.upsert(request_id, {
            "employee_id": state.employee_id, "leave_type": state.leave_type,
            "start_date": state.start_date, "end_date": state.end_date,
            "requested_days": requested, "reason": state.leave_reason,
            "eligibility_status": state.eligibility_status, "balance_status": state.balance_status,
            "staffing_status": state.staffing_status, "approval_required": result.approval_required,
            "approval_status": state.approval_status, "decision": state.leave_decision,
            "decision_reason": result.reason, "reserved_days": desired_reserved,
            "custom_data": {"clarification_question": result.clarification_question},
            "decided_at": datetime.now(UTC) if state.leave_decision != LeaveDecision.PENDING else None,
            "cancelled_at": datetime.now(UTC) if state.leave_decision == LeaveDecision.CANCELLED else None,
        })

    @staticmethod
    def _query(context: DepartmentExecutionContext) -> str:
        parts = [context.request_summary, context.latest_user_input or ""]
        if context.collaboration_input:
            parts.extend(str(value) for value in context.collaboration_input.payload.values() if value)
        return "\n".join(parts)[:2000]

    @staticmethod
    def _evidence(item: Any) -> dict[str, Any]:
        return {"document_id": str(item.document_id), "title": item.title,
            "document_type": item.document_type.value, "version": item.version,
            "chunk_index": item.chunk_index, "effective_date": item.effective_date.isoformat() if item.effective_date else None,
            "content": item.chunk_text}

    @staticmethod
    def _leave_data(record: Any) -> dict[str, Any]:
        if record is None:
            return {}
        return {"employee_id": str(record.employee_id), "leave_type": record.leave_type.value,
            "start_date": record.start_date.isoformat(), "end_date": record.end_date.isoformat(),
            "requested_days": str(record.requested_days), "eligibility_status": record.eligibility_status.value,
            "balance_status": record.balance_status.value, "staffing_status": record.staffing_status.value,
            "approval_status": record.approval_status.value, "decision": record.decision.value,
            "reserved_days": str(record.reserved_days)}

    @staticmethod
    def _onboarding_data(record: Any) -> dict[str, Any]:
        if record is None:
            return {}
        return {"employee_id": str(record.employee_id), "start_date": record.start_date.isoformat(),
            "department_id": str(record.department_id), "manager_employee_id": str(record.manager_employee_id) if record.manager_employee_id else None,
            "status": record.onboarding_status.value, "required_actions": record.required_actions,
            "completed_actions": record.completed_actions, "missing_data": record.missing_data}
