from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.enums import DepartmentType
from app.departments.contracts import (
    DepartmentCollaborationUpdates,
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
from app.departments.procurement.enums import ProcurementModelRole
from app.departments.procurement.model_policy import (
    initial_model_role,
    requires_reasoning_pass,
)
from app.departments.procurement.repository import (
    ProcurementRequestRepository,
    SupplierCandidateRepository,
)
from app.departments.procurement.schemas import (
    ProcurementDepartmentResult,
    ProcurementExecutionInput,
    SupplierCandidateCreate,
    SupplierCandidateUpdate,
)
from app.departments.procurement.scoring import (
    CandidateEvaluation,
    CandidateFacts,
    ProcurementCalculationError,
    calculate_total_cost,
    evaluate_and_rank,
    normalize_currency,
    quantity,
)
from app.llm.groq import GroqProcurementClient
from app.rag.enums import KnowledgeDepartmentScope
from app.rag.retrieval import KnowledgeRetrievalService
from app.rag.schemas import KnowledgeRetrievalQuery


class ProcurementService:
    def __init__(
        self,
        session: AsyncSession,
        requester: AuthenticatedUser,
        settings: Settings,
        retrieval: KnowledgeRetrievalService,
        *,
        llm_client: Any | None = None,
        request_repository: ProcurementRequestRepository | None = None,
        candidate_repository: SupplierCandidateRepository | None = None,
    ) -> None:
        self.session = session
        self.requester = requester
        self.settings = settings
        self.retrieval = retrieval
        self.llm = llm_client or GroqProcurementClient(settings)
        self.requests = request_repository or ProcurementRequestRepository(
            session, requester.company_id
        )
        self.candidates = candidate_repository or SupplierCandidateRepository(
            session, requester.company_id
        )

    async def execute(
        self, context: DepartmentExecutionContext
    ) -> DepartmentExecutionResult:
        model_input, records, evaluations = await self._build_input(context)
        await self.session.rollback()
        evidence = await self.retrieval.search_trusted(
            KnowledgeRetrievalQuery(
                company_id=context.company_id,
                query_text=self._query(context, model_input.purchase_requirement),
                departments=[
                    KnowledgeDepartmentScope.PROCUREMENT,
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
            result = await self.llm.generate(
                model_input, role=ProcurementModelRole.REASONING
            )
        self._validate(result, evidence, model_input, records, evaluations)
        return self._to_department_result(result)

    async def _build_input(
        self, context: DepartmentExecutionContext
    ) -> tuple[ProcurementExecutionInput, list[Any], list[CandidateEvaluation]]:
        existing = await self.requests.get(context.request_id)
        records = await self.candidates.list_for_request(context.request_id) if existing else []
        payload = context.collaboration_input.payload if context.collaboration_input else {}
        custom = context.relevant_custom_data
        requirement = self._requirement(existing, payload, custom, context)
        weights = requirement.get("evaluation_criteria", {}).get("weights")
        evaluations: list[CandidateEvaluation] = []
        if records and isinstance(weights, dict):
            evaluations = evaluate_and_rank(
                [self._facts(item) for item in records], weights
            )
        evaluation_by_id = {item.candidate_id: item for item in evaluations}
        candidate_data = [
            self._candidate_data(item, evaluation_by_id.get(item.id)) for item in records
        ]
        collaboration_result = (
            context.collaboration_result.result if context.collaboration_result else {}
        )
        finance_result = (
            collaboration_result
            if context.collaboration_result
            and context.collaboration_result.sender_department == DepartmentType.FINANCE
            else {}
        )
        origin = (
            context.collaboration_input.sender_department
            if context.collaboration_input
            else None
        )
        return (
            ProcurementExecutionInput(
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
                purchase_requirement=requirement,
                candidates=candidate_data,
                finance_result=finance_result,
                approval_state=(
                    context.human_response.model_dump(mode="json")
                    if context.human_response
                    else {}
                ),
                collaboration_input=context.collaboration_input,
                collaboration_result=context.collaboration_result,
                tool_results=context.tool_results,
                previous_procurement_state=context.department_data,
            ),
            records,
            evaluations,
        )

    @staticmethod
    def _requirement(
        existing: Any,
        payload: dict[str, Any],
        custom: dict[str, Any],
        context: DepartmentExecutionContext,
    ) -> dict[str, Any]:
        stored = (
            {
                "item_or_service": existing.item_or_service,
                "quantity": str(existing.quantity),
                "minimum_specifications": existing.minimum_specifications,
                "required_certifications": existing.required_certifications,
                "delivery_location": existing.delivery_location,
                "required_by_date": (
                    existing.required_by_date.isoformat()
                    if existing.required_by_date
                    else None
                ),
                "estimated_budget": (
                    str(existing.estimated_budget)
                    if existing.estimated_budget is not None
                    else None
                ),
                "approved_budget": (
                    str(existing.approved_budget)
                    if existing.approved_budget is not None
                    else None
                ),
                "currency": existing.currency,
                "evaluation_criteria": existing.evaluation_criteria,
            }
            if existing
            else {}
        )
        aliases = {
            "item_or_service": ("item_or_service", "requested_asset", "asset_type"),
            "quantity": ("quantity",),
            "minimum_specifications": ("minimum_specifications", "minimum_specification"),
            "required_certifications": ("required_certifications",),
            "delivery_location": ("delivery_location",),
            "required_by_date": ("required_by_date", "delivery_deadline"),
            "estimated_budget": ("estimated_budget", "estimated_cost"),
            "approved_budget": ("approved_budget",),
            "currency": ("currency",),
            "evaluation_criteria": ("evaluation_criteria", "ranking_criteria"),
        }
        requirement = dict(stored)
        for target, keys in aliases.items():
            for source in (payload, custom):
                value = next((source[key] for key in keys if source.get(key) is not None), None)
                if value is not None:
                    requirement[target] = value
                    break
        requirement.setdefault("business_reason", context.request_summary)
        return requirement

    @staticmethod
    def _facts(candidate: Any) -> CandidateFacts:
        return CandidateFacts(
            id=candidate.id,
            supplier_name=candidate.supplier_name,
            total_cost=candidate.total_cost,
            currency=candidate.currency,
            delivery_days=candidate.delivery_days,
            quality_score=candidate.quality_score,
            meets_minimum_specification=candidate.meets_minimum_specification,
            compliance_status=candidate.compliance_status,
            availability_status=candidate.availability_status,
        )

    @staticmethod
    def _candidate_data(candidate: Any, evaluation: CandidateEvaluation | None) -> dict[str, Any]:
        return {
            "candidate_id": str(candidate.id),
            "supplier_name": candidate.supplier_name,
            "item_or_service": candidate.item_or_service,
            "total_cost": str(candidate.total_cost),
            "currency": candidate.currency,
            "delivery_days": candidate.delivery_days,
            "warranty_months": candidate.warranty_months,
            "meets_minimum_specification": candidate.meets_minimum_specification,
            "compliance_status": candidate.compliance_status.value,
            "availability_status": candidate.availability_status.value,
            "quality_score": (
                str(candidate.quality_score) if candidate.quality_score is not None else None
            ),
            "deterministic_evaluation": (
                {
                    "eligible": evaluation.eligible,
                    "price_score": str(evaluation.price_score),
                    "delivery_score": str(evaluation.delivery_score),
                    "compliance_score": str(evaluation.compliance_score),
                    "overall_score": str(evaluation.overall_score),
                    "rank": evaluation.rank,
                }
                if evaluation and evaluation.eligible
                else {"eligible": False}
            ),
        }

    @staticmethod
    def _query(context: DepartmentExecutionContext, requirement: dict[str, Any]) -> str:
        parts = [
            context.request_summary,
            context.latest_user_input or "",
            str(requirement.get("item_or_service", "")),
            str(requirement.get("minimum_specifications", "")),
            str(requirement.get("required_certifications", "")),
        ]
        return "\n".join(item for item in parts if item)[:2000]

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
        result: ProcurementDepartmentResult,
        evidence: list[Any],
        context: ProcurementExecutionInput,
        records: list[Any],
        evaluations: list[CandidateEvaluation],
    ) -> None:
        allowed_sources = {
            (item.document_id, item.title, item.document_type, item.version, item.chunk_index)
            for item in evidence
        }
        if any(
            (source.document_id, source.title, source.document_type, source.version, source.chunk_index)
            not in allowed_sources
            for source in result.sources_used
        ):
            raise ValueError("Procurement returned an unauthorized source reference")
        if result.clarification_question and (
            result.clarification_question
            == context.previous_procurement_state.get("clarification_question")
        ):
            raise ValueError("Procurement repeated a clarification question")
        if result.candidate_count != len(records):
            raise ValueError("Procurement candidate count conflicts with trusted data")
        eligible = [item for item in evaluations if item.eligible]
        if result.eligible_candidate_count != len(eligible):
            raise ValueError("Procurement eligibility conflicts with backend evaluation")
        evaluation_by_id = {item.candidate_id: item for item in eligible}
        record_by_id = {item.id: item for item in records}
        for item in result.shortlist:
            evaluation = evaluation_by_id.get(item.candidate_id)
            record = record_by_id.get(item.candidate_id)
            if evaluation is None or record is None:
                raise ValueError("Procurement shortlisted an ineligible candidate")
            if (
                item.total_cost != record.total_cost
                or item.currency != record.currency
                or item.rank != evaluation.rank
                or item.overall_score != evaluation.overall_score
            ):
                raise ValueError("Procurement changed deterministic candidate facts")
        finance = context.finance_result
        finance_approved = bool(
            finance
            and (
                finance.get("budget_validated")
                or (
                    finance.get("budget_sufficient") is True
                    and finance.get("approval_required") is False
                )
            )
        )
        if result.finance_result_received != bool(finance):
            raise ValueError("Procurement Finance-result state is inconsistent")
        if (
            result.state_updates.finance_validation_status.value == "approved"
            and not finance_approved
        ):
            raise ValueError("Procurement invented Finance approval")
        if finance:
            if not finance_approved and result.state_updates.selected_candidate_id:
                raise ValueError("Finance did not authorize supplier selection")
        if result.state_updates.selected_candidate_id is not None:
            human_decision = str(context.approval_state.get("decision", "")).casefold()
            if human_decision not in {"approved", "selected", "approve", "select"}:
                raise ValueError("Trusted human supplier authorization is required")

    @staticmethod
    def _to_department_result(
        result: ProcurementDepartmentResult,
    ) -> DepartmentExecutionResult:
        status = {
            "wait_for_user_input": DepartmentExecutionStatus.WAITING_FOR_USER,
            "execute_tool": DepartmentExecutionStatus.WAITING_FOR_TOOL,
            "collaborate": DepartmentExecutionStatus.WAITING_FOR_DEPARTMENT,
            "request_human_action": DepartmentExecutionStatus.WAITING_FOR_HUMAN,
            "fail_request": DepartmentExecutionStatus.UNSUPPORTED,
        }.get(result.next_action.value, DepartmentExecutionStatus.COMPLETED)
        stage = {
            "wait_for_user_input": "procurement_waiting_for_user",
            "execute_tool": "procurement_executing_controlled_operation",
            "collaborate": "procurement_waiting_for_finance",
            "request_human_action": "procurement_waiting_for_selection",
            "fail_request": "procurement_failed",
        }.get(result.next_action.value, "procurement_completed")
        return DepartmentExecutionResult(
            department_type=DepartmentType.PROCUREMENT,
            status=status,
            decision=result.decision.value,
            reason=result.reason,
            user_message=result.user_message,
            current_stage=stage,
            completed_step="procurement_analysis_completed",
            next_action=result.next_action,
            requires_tool=result.requires_tool,
            tool_request=result.tool_request,
            requires_collaboration=result.requires_finance_collaboration,
            collaboration_request=result.finance_collaboration_request,
            next_department=(
                DepartmentType.FINANCE if result.requires_finance_collaboration else None
            ),
            requires_human_action=result.requires_human_action,
            human_action_request=result.human_action_request,
            is_terminal=result.next_action.value in {"complete_request", "fail_request"},
            safe_event_title=result.safe_event_title,
            safe_event_message=result.safe_event_message,
            state_updates=DepartmentStateUpdates(
                execution=DepartmentExecutionUpdates(
                    last_operation="procurement_analysis",
                    last_operation_status=status.value,
                    department_data=result.model_dump(mode="json"),
                ),
                routing=(
                    DepartmentRoutingUpdates(
                        needs_clarification=True,
                        latest_question=result.clarification_question,
                        routing_pending=False,
                    )
                    if result.needs_user_clarification
                    else None
                ),
                collaboration=(
                    DepartmentCollaborationUpdates(
                        request=result.finance_collaboration_request,
                        is_active=True,
                    )
                    if result.requires_finance_collaboration
                    else None
                ),
                human_action=(
                    DepartmentHumanActionUpdates(
                        required=True, request=result.human_action_request
                    )
                    if result.requires_human_action
                    else None
                ),
                result=DepartmentResultUpdates(
                    decision=result.decision.value,
                    reason=result.reason,
                    final_response=result.user_message,
                ),
            ),
        )

    async def persist_result(
        self, request_id: UUID, result: ProcurementDepartmentResult
    ) -> None:
        state = result.state_updates
        if not state.item_or_service or state.quantity is None or not state.currency:
            if result.category.value == "procurement_information":
                return
            raise ProcurementCalculationError(
                "structured purchase requirements are incomplete"
            )
        await self.requests.upsert(
            request_id,
            {
                "requesting_department_id": state.requesting_department_id,
                "category": result.category,
                "item_or_service": state.item_or_service,
                "quantity": quantity(state.quantity),
                "minimum_specifications": state.minimum_specifications,
                "required_certifications": state.required_certifications,
                "delivery_location": state.delivery_location,
                "required_by_date": state.required_by_date,
                "estimated_budget": state.estimated_budget,
                "approved_budget": state.approved_budget,
                "currency": normalize_currency(state.currency),
                "evaluation_criteria": state.evaluation_criteria,
                "finance_validation_status": state.finance_validation_status,
                "shortlist_status": state.shortlist_status,
                "selected_candidate_id": state.selected_candidate_id,
                "selection_status": state.selection_status,
                "custom_data": {
                    "clarification_question": result.clarification_question,
                    "recommendation_reason": result.recommendation_reason,
                },
                "completed_at": (
                    datetime.now(UTC)
                    if result.next_action.value in {"complete_request", "fail_request"}
                    else None
                ),
            },
        )
        records = await self.candidates.list_for_request(request_id, for_update=True)
        weights = state.evaluation_criteria.get("weights")
        if records and isinstance(weights, dict):
            evaluations = evaluate_and_rank([self._facts(item) for item in records], weights)
            shortlist_ids = {item.candidate_id for item in result.shortlist}
            by_id = {item.id: item for item in records}
            for evaluation in evaluations:
                candidate = by_id[evaluation.candidate_id]
                candidate.price_score = evaluation.price_score
                candidate.delivery_score = evaluation.delivery_score
                candidate.compliance_score = evaluation.compliance_score
                candidate.overall_score = evaluation.overall_score
                candidate.rank = evaluation.rank
                candidate.evaluation_reason = evaluation.reason
                candidate.is_shortlisted = candidate.id in shortlist_ids
                candidate.is_selected = candidate.id == state.selected_candidate_id
            await self.session.flush()

    @staticmethod
    async def create_managed_candidate(
        session: AsyncSession,
        company_id: UUID,
        request_id: UUID,
        payload: SupplierCandidateCreate,
    ) -> Any:
        request_record = await ProcurementRequestRepository(
            session, company_id
        ).get(request_id, for_update=True)
        if request_record is None:
            return None
        values = payload.model_dump()
        values["total_cost"] = calculate_total_cost(
            payload.quoted_unit_price,
            payload.quantity,
            payload.delivery_cost,
            payload.tax_amount or 0,
        )
        try:
            record = await SupplierCandidateRepository(session, company_id).create(
                request_id, values
            )
            await session.commit()
            return record
        except Exception:
            await session.rollback()
            raise

    @staticmethod
    async def update_managed_candidate(
        session: AsyncSession,
        company_id: UUID,
        candidate_id: UUID,
        payload: SupplierCandidateUpdate,
    ) -> tuple[Any | None, bool]:
        repository = SupplierCandidateRepository(session, company_id)
        record = await repository.get(candidate_id, for_update=True)
        if record is None:
            return None, False
        if record.is_selected:
            return record, True
        values = payload.model_dump(exclude_unset=True)
        if values.get("custom_data") is None:
            values.pop("custom_data", None)
        values["total_cost"] = calculate_total_cost(
            values.get("quoted_unit_price", record.quoted_unit_price),
            values.get("quantity", record.quantity),
            values.get("delivery_cost", record.delivery_cost),
            values.get("tax_amount", record.tax_amount or 0),
        )
        values.update(
            {
                "price_score": None,
                "delivery_score": None,
                "compliance_score": None,
                "overall_score": None,
                "rank": None,
                "evaluation_reason": None,
                "is_shortlisted": False,
            }
        )
        try:
            updated = await repository.update(candidate_id, values)
            await session.commit()
            return updated, False
        except Exception:
            await session.rollback()
            raise
