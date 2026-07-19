from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.enums import DepartmentType
from app.departments.contracts import (
    DepartmentCollaborationUpdates, DepartmentExecutionContext, DepartmentExecutionResult,
    DepartmentExecutionStatus, DepartmentExecutionUpdates, DepartmentHumanActionUpdates,
    DepartmentResultUpdates, DepartmentRoutingUpdates, DepartmentStateUpdates,
)
from app.departments.it.enums import (
    HardwareAssignmentStatus, IncidentStatus, ITModelRole, ProvisioningStatus,
)
from app.departments.it.model_policy import initial_model_role, requires_reasoning_pass
from app.departments.it.repository import (
    AccessRequestRepository, AssetRepository, HardwareRequestRepository,
    ITIncidentRepository, SoftwareCatalogRepository,
)
from app.departments.it.schemas import ITDepartmentResult, ITExecutionInput
from app.employees.repository import EmployeeRepository
from app.llm.groq import GroqITClient
from app.rag.enums import KnowledgeDepartmentScope
from app.rag.retrieval import KnowledgeRetrievalService
from app.rag.schemas import KnowledgeRetrievalQuery
from app.departments.customer_support.service import requester_access_scopes


class ITService:
    def __init__(self, session: AsyncSession, requester: AuthenticatedUser, settings: Settings,
        retrieval: KnowledgeRetrievalService, *, llm_client: Any | None = None,
        access_repository: AccessRequestRepository | None = None,
        hardware_repository: HardwareRequestRepository | None = None,
        incident_repository: ITIncidentRepository | None = None,
        asset_repository: AssetRepository | None = None,
        software_repository: SoftwareCatalogRepository | None = None,
        employee_repository: EmployeeRepository | None = None) -> None:
        self.session, self.requester, self.settings, self.retrieval = session, requester, settings, retrieval
        company_id = requester.company_id
        self.llm = llm_client or GroqITClient(settings)
        self.access = access_repository or AccessRequestRepository(session, company_id)
        self.hardware = hardware_repository or HardwareRequestRepository(session, company_id)
        self.incidents = incident_repository or ITIncidentRepository(session, company_id)
        self.assets = asset_repository or AssetRepository(session, company_id)
        self.software = software_repository or SoftwareCatalogRepository(session, company_id)
        self.employees = employee_repository or EmployeeRepository(session, company_id)

    async def execute(self, context: DepartmentExecutionContext) -> DepartmentExecutionResult:
        model_input = await self._build_input(context)
        await self.session.rollback()
        rag = await self.retrieval.search_trusted(KnowledgeRetrievalQuery(
            company_id=context.company_id, query_text=self._query(context),
            departments=[KnowledgeDepartmentScope.IT, KnowledgeDepartmentScope.SHARED],
            allowed_access_scopes=requester_access_scopes(AuthenticatedUser(
                user_id=context.requester_user_id, company_id=context.company_id, email="trusted-requester@internal.invalid",
                actor_type=context.requester_actor_type, employee_id=context.requester_employee_id,
                department_id=context.requester_department_id, is_manager=context.requester_is_manager)),
            top_k=self.settings.rag_top_k))
        await self.session.rollback()
        model_input = model_input.model_copy(update={"evidence": [self._evidence(item) for item in rag]})
        role = initial_model_role(model_input)
        result = await self.llm.generate(model_input, role=role)
        if requires_reasoning_pass(result, role):
            result = await self.llm.generate(model_input, role=ITModelRole.REASONING)
        self._validate(result, rag, model_input)
        return self._to_department_result(result)

    async def _build_input(self, context: DepartmentExecutionContext) -> ITExecutionInput:
        employee = await self.employees.get_by_id(context.requester_employee_id) if context.requester_employee_id else None
        assigned = await self.assets.assigned_to(employee.id) if employee else []
        existing_access = await self.access.list_for_employee(employee.id) if employee else []
        return ITExecutionInput(
            request_id=context.request_id, company_id=context.company_id,
            requester_user_id=context.requester_user_id, requester_employee_id=context.requester_employee_id,
            requester_department_id=context.requester_department_id,
            requester_actor_type=context.requester_actor_type,
            requester_is_manager=context.requester_is_manager,
            request_type=context.request_type, original_summary=context.request_summary,
            latest_user_input=context.latest_user_input, current_stage=context.current_stage,
            completed_it_steps=context.completed_steps,
            employee_data=({"employee_id": str(employee.id), "department_id": str(employee.department_id) if employee.department_id else None,
                "job_title": employee.job_title, "employment_status": employee.employment_status.value} if employee else {}),
            existing_access=[{"target_system": item.target_system, "access_type": item.access_type.value,
                "status": item.provisioning_status.value} for item in existing_access],
            assigned_assets=[{"asset_id": str(item.id), "asset_type": item.asset_type,
                "brand": item.brand, "model": item.model, "status": item.status.value} for item in assigned],
            inventory_results=[item for item in context.tool_results if item.get("operation") == "check_asset_inventory"],
            software_results=[item for item in context.tool_results if item.get("operation") == "check_software_availability"],
            collaboration_input=context.collaboration_input,
            collaboration_result=context.collaboration_result,
            review_feedback=context.review_feedback.model_dump(mode="json") if context.review_feedback else {},
            human_response=context.human_response.model_dump(mode="json") if context.human_response else {},
            previous_it_state=context.department_data,
        )

    @staticmethod
    def _query(context: DepartmentExecutionContext) -> str:
        parts = [context.request_summary, context.latest_user_input or ""]
        if context.collaboration_input:
            parts.extend(str(value) for value in context.collaboration_input.payload.values() if value)
        return "\n".join(item for item in parts if item)[:2000]

    @staticmethod
    def _evidence(item: Any) -> dict[str, Any]:
        return {"document_id": str(item.document_id), "title": item.title,
            "document_type": item.document_type.value, "version": item.version,
            "chunk_index": item.chunk_index, "effective_date": item.effective_date.isoformat() if item.effective_date else None,
            "content": item.chunk_text}

    @staticmethod
    def _validate(result: ITDepartmentResult, evidence: list[Any], context: ITExecutionInput) -> None:
        allowed = {(item.document_id, item.title, item.document_type, item.version, item.chunk_index) for item in evidence}
        if any((source.document_id, source.title, source.document_type, source.version, source.chunk_index) not in allowed for source in result.sources_used):
            raise ValueError("IT returned an unauthorized source reference")
        if result.requires_procurement_collaboration:
            collaboration = context.collaboration_result
            if (
                collaboration is None
                or collaboration.sender_department != DepartmentType.FINANCE
                or collaboration.receiver_department != DepartmentType.IT
                or collaboration.action != "validate_it_purchase_budget"
                or collaboration.status.value != "completed"
                or not (
                    collaboration.result.get("budget_validated") is True
                    or (
                        collaboration.result.get("budget_sufficient") is True
                        and collaboration.result.get("approval_required") is False
                    )
                )
            ):
                raise ValueError("Procurement preparation requires trusted Finance validation")
        previous_question = context.previous_it_state.get("clarification_question")
        if result.clarification_question and result.clarification_question == previous_question:
            raise ValueError("IT repeated a clarification question")
        previous = context.previous_it_state.get("state_updates", {}).get("incident", {}).get("diagnostic_steps", [])
        previous_ids = {item.get("step_id") for item in previous}
        incident = result.state_updates.incident
        if incident and any(step.step_id in previous_ids and not step.completed for step in incident.diagnostic_steps):
            raise ValueError("IT repeated an incomplete diagnostic step")

    @staticmethod
    def _to_department_result(result: ITDepartmentResult) -> DepartmentExecutionResult:
        status = {"wait_for_user_input": DepartmentExecutionStatus.WAITING_FOR_USER,
            "execute_tool": DepartmentExecutionStatus.WAITING_FOR_TOOL,
            "collaborate": DepartmentExecutionStatus.WAITING_FOR_DEPARTMENT,
            "request_human_action": DepartmentExecutionStatus.WAITING_FOR_HUMAN,
            "fail_request": DepartmentExecutionStatus.UNSUPPORTED}.get(result.next_action.value, DepartmentExecutionStatus.COMPLETED)
        stage = {"wait_for_user_input": "it_waiting_for_user", "execute_tool": "it_checking_company_data",
            "collaborate": "it_waiting_for_department", "request_human_action": "it_waiting_for_technician",
            "fail_request": "it_failed"}.get(result.next_action.value, "it_completed")
        collaboration = result.finance_collaboration_request or result.procurement_collaboration_request
        return DepartmentExecutionResult(
            department_type=DepartmentType.IT, status=status, decision=result.decision.value,
            reason=result.reason, user_message=result.user_message, current_stage=stage,
            completed_step="it_analysis_completed", next_action=result.next_action,
            next_department=collaboration.receiver_department if collaboration else None,
            requires_tool=result.requires_tool, tool_request=result.tool_request,
            requires_collaboration=collaboration is not None, collaboration_request=collaboration,
            requires_human_action=result.requires_human_action, human_action_request=result.human_action_request,
            is_terminal=result.next_action.value in {"complete_request", "fail_request"},
            safe_event_title=result.safe_event_title, safe_event_message=result.safe_event_message,
            state_updates=DepartmentStateUpdates(
                execution=DepartmentExecutionUpdates(last_operation="it_analysis",
                    last_operation_status=status.value, department_data=result.model_dump(mode="json")),
                routing=(DepartmentRoutingUpdates(needs_clarification=True,
                    latest_question=result.clarification_question, routing_pending=False) if result.needs_user_clarification else None),
                collaboration=(DepartmentCollaborationUpdates(request=collaboration, is_active=True) if collaboration else None),
                human_action=(DepartmentHumanActionUpdates(required=True,
                    request=result.human_action_request) if result.requires_human_action else None),
                result=DepartmentResultUpdates(decision=result.decision.value,
                    reason=result.reason, final_response=result.user_message)))

    async def persist_result(self, request_id: Any, result: ITDepartmentResult,
        *, reported_by_user_id: Any) -> None:
        if result.state_updates.access:
            state = result.state_updates.access
            if state.employee_id is None or state.access_type is None or not state.target_system or not state.business_reason:
                raise ValueError("Access persistence requires trusted structured fields")
            await self.access.upsert(request_id, {"employee_id": state.employee_id,
                "access_type": state.access_type, "target_system": state.target_system,
                "requested_role": state.requested_role, "business_reason": state.business_reason,
                "policy_decision": state.policy_decision, "approval_required": state.approval_required,
                "provisioning_status": state.provisioning_status, "custom_data": {},
                "completed_at": datetime.now(UTC) if state.provisioning_status == ProvisioningStatus.COMPLETED else None})
        if result.state_updates.hardware:
            state = result.state_updates.hardware
            if state.employee_id is None or not state.asset_type or not state.business_reason:
                raise ValueError("Hardware persistence requires trusted structured fields")
            await self.hardware.upsert(request_id, {"employee_id": state.employee_id,
                "asset_type": state.asset_type, "requested_specification": state.requested_specification,
                "business_reason": state.business_reason, "inventory_checked": state.inventory_checked,
                "available_asset_id": state.available_asset_id, "estimated_cost": state.estimated_cost,
                "budget_validation_required": state.budget_validation_required,
                "procurement_required": state.procurement_required,
                "assignment_status": state.assignment_status, "custom_data": {},
                "completed_at": datetime.now(UTC) if state.assignment_status == HardwareAssignmentStatus.COMPLETED else None})
        if result.state_updates.incident:
            state = result.state_updates.incident
            await self.incidents.upsert(request_id, {"reported_by_user_id": reported_by_user_id,
                "affected_employee_id": state.affected_employee_id, "source": state.source,
                "category": result.category, "summary": result.user_message,
                "symptoms": state.symptoms, "error_messages": state.error_messages,
                "impact": state.impact, "urgency": state.urgency,
                "diagnostic_steps": [item.model_dump(mode="json") for item in state.diagnostic_steps],
                "resolution_summary": state.resolution_summary,
                "incident_status": IncidentStatus.RESOLVED if result.incident_resolved else (IncidentStatus.WAITING_TECHNICIAN if state.requires_human_technician else IncidentStatus.DIAGNOSING),
                "requires_human_technician": state.requires_human_technician,
                "custom_data": {}, "resolved_at": datetime.now(UTC) if result.incident_resolved else None})
