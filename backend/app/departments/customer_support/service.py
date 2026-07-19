from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.enums import ActorType, DepartmentType
from app.departments.contracts import (
    DepartmentExecutionContext,
    DepartmentExecutionResult,
    DepartmentExecutionStatus,
    DepartmentExecutionUpdates,
    DepartmentCollaborationUpdates,
    DepartmentHumanActionUpdates,
    DepartmentResultUpdates,
    DepartmentRoutingUpdates,
    DepartmentStateUpdates,
)
from app.departments.customer_support.enums import SupportIssueStatus
from app.departments.customer_support.model_policy import requires_reasoning_pass
from app.departments.customer_support.repository import SupportIssueRepository
from app.departments.customer_support.schemas import CustomerSupportModelInput, CustomerSupportResult
from app.llm.groq import GroqCustomerSupportClient, SupportModelRole
from app.rag.enums import KnowledgeAccessScope, KnowledgeDepartmentScope
from app.rag.retrieval import KnowledgeRetrievalService
from app.rag.schemas import KnowledgeRetrievalQuery


def requester_access_scopes(user: AuthenticatedUser) -> list[KnowledgeAccessScope]:
    scopes = [KnowledgeAccessScope.ALL_AUTHENTICATED]
    if user.actor_type in {ActorType.EMPLOYEE, ActorType.DEPARTMENT_MANAGER}:
        scopes.append(KnowledgeAccessScope.EMPLOYEES)
    if user.actor_type == ActorType.DEPARTMENT_MANAGER and user.is_manager:
        scopes.append(KnowledgeAccessScope.DEPARTMENT_MANAGERS)
    if user.actor_type == ActorType.COMPANY:
        scopes.extend(
            [KnowledgeAccessScope.EMPLOYEES, KnowledgeAccessScope.DEPARTMENT_MANAGERS,
             KnowledgeAccessScope.COMPANY_ACCOUNT, KnowledgeAccessScope.INTERNAL_SYSTEM]
        )
    return list(dict.fromkeys(scopes))


class CustomerSupportService:
    def __init__(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        settings: Settings,
        retrieval_service: KnowledgeRetrievalService,
        *,
        llm_client: GroqCustomerSupportClient | Any | None = None,
        issue_repository: SupportIssueRepository | None = None,
    ) -> None:
        self.session = session
        self.current_user = current_user
        self.settings = settings
        self.retrieval = retrieval_service
        self.llm = llm_client or GroqCustomerSupportClient(settings)
        self.issues = issue_repository or SupportIssueRepository(session, current_user.company_id)

    async def execute(self, context: DepartmentExecutionContext) -> DepartmentExecutionResult:
        issue = await self.issues.get(context.request_id)
        issue_history = self._issue_history(issue)
        await self.session.rollback()  # release read transaction before Pinecone/Groq
        query_text = self._query_text(context, issue_history)
        evidence = await self.retrieval.search_trusted(
            KnowledgeRetrievalQuery(
                company_id=context.company_id,
                query_text=query_text,
                departments=[KnowledgeDepartmentScope.CUSTOMER_SUPPORT, KnowledgeDepartmentScope.SHARED],
                allowed_access_scopes=requester_access_scopes(self.current_user),
                top_k=self.settings.rag_top_k,
            )
        )
        await self.session.rollback()  # release document-validation transaction
        payload = CustomerSupportModelInput(
            request_id=context.request_id,
            message=context.request_summary,
            latest_user_input=context.latest_user_input,
            evidence=[self._evidence(item) for item in evidence],
            issue_history=issue_history,
            it_collaboration_result=context.collaboration_result,
        )
        result = await self.llm.generate(payload, role=SupportModelRole.FAST)
        if requires_reasoning_pass(result):
            result = await self.llm.generate(payload, role=SupportModelRole.REASONING)
        self._validate_sources(result, evidence)
        department_result = self._to_department_result(result)
        if context.collaboration_result is not None:
            updates = department_result.state_updates.model_copy(update={
                "collaboration": DepartmentCollaborationUpdates(is_active=False)})
            department_result = department_result.model_copy(update={"state_updates": updates})
        return department_result

    @staticmethod
    def _query_text(context: DepartmentExecutionContext, history: dict[str, Any]) -> str:
        parts = [context.request_summary]
        if context.latest_user_input:
            parts.append(context.latest_user_input)
        parts.extend(history.get("symptoms", []))
        parts.extend(history.get("error_messages", []))
        return "\n".join(str(item) for item in parts if item)[:2000]

    @staticmethod
    def _issue_history(issue: Any | None) -> dict[str, Any]:
        if issue is None:
            return {}
        return {
            "category": issue.category.value,
            "status": issue.issue_status.value,
            "symptoms": issue.symptoms,
            "error_messages": issue.error_messages,
            "troubleshooting_steps": issue.troubleshooting_steps,
            "asked_questions": issue.custom_data.get("asked_questions", []),
        }

    @staticmethod
    def _evidence(item: Any) -> dict[str, Any]:
        return {
            "document_id": str(item.document_id), "title": item.title,
            "document_type": item.document_type.value, "version": item.version,
            "chunk_index": item.chunk_index, "effective_date": (
                item.effective_date.isoformat() if item.effective_date else None),
            "content": item.chunk_text,
        }

    @staticmethod
    def _validate_sources(result: CustomerSupportResult, evidence: list[Any]) -> None:
        allowed = {
            (item.document_id, item.title, item.document_type, item.version, item.chunk_index)
            for item in evidence
        }
        if any(
            (source.document_id, source.title, source.document_type,
             source.version, source.chunk_index) not in allowed
            for source in result.sources
        ):
            raise ValueError("Customer Support returned an unauthorized source reference")

    @staticmethod
    def _to_department_result(result: CustomerSupportResult) -> DepartmentExecutionResult:
        status = {
            "wait_for_user_input": DepartmentExecutionStatus.WAITING_FOR_USER,
            "collaborate": DepartmentExecutionStatus.WAITING_FOR_DEPARTMENT,
            "request_human_action": DepartmentExecutionStatus.WAITING_FOR_HUMAN,
            "fail_request": DepartmentExecutionStatus.UNSUPPORTED,
        }.get(result.next_action.value, DepartmentExecutionStatus.COMPLETED)
        stage = {
            "wait_for_user_input": "customer_support_waiting_for_customer",
            "collaborate": "customer_support_waiting_for_it",
            "request_human_action": "customer_support_waiting_for_human_support",
            "fail_request": "customer_support_failed",
        }.get(result.next_action.value, "customer_support_completed")
        return DepartmentExecutionResult(
            department_type=DepartmentType.CUSTOMER_SUPPORT,
            status=status,
            decision=result.decision.value,
            reason=result.reason,
            user_message=result.answer,
            current_stage=stage,
            completed_step="customer_support_analysis_completed",
            next_action=result.next_action,
            next_department=(DepartmentType.IT if result.requires_it_collaboration else None),
            requires_collaboration=result.requires_it_collaboration,
            collaboration_request=result.it_collaboration_request,
            requires_human_action=result.requires_human_escalation,
            human_action_request=result.human_action_request,
            is_terminal=result.next_action.value in {"complete_request", "fail_request"},
            safe_event_title=result.safe_event_title,
            safe_event_message=result.safe_event_message,
            state_updates=DepartmentStateUpdates(
                execution=DepartmentExecutionUpdates(
                    last_operation="customer_support_analysis",
                    last_operation_status=status.value,
                    department_data=result.model_dump(mode="json"),
                ),
                routing=(DepartmentRoutingUpdates(
                    needs_clarification=True,
                    latest_question=result.clarification_question,
                    routing_pending=False,
                ) if result.needs_clarification else None),
                collaboration=(DepartmentCollaborationUpdates(
                    request=result.it_collaboration_request,
                    is_active=True,
                ) if result.requires_it_collaboration else None),
                human_action=(DepartmentHumanActionUpdates(
                    required=True,
                    request=result.human_action_request,
                ) if result.requires_human_escalation else None),
                result=DepartmentResultUpdates(
                    decision=result.decision.value, reason=result.reason,
                    final_response=result.answer,
                ),
            ),
        )

    async def persist_result(self, request_id: Any, result: CustomerSupportResult) -> None:
        status = {
            "wait_for_user_input": SupportIssueStatus.WAITING_FOR_CUSTOMER,
            "collaborate": SupportIssueStatus.WAITING_FOR_IT,
            "request_human_action": SupportIssueStatus.WAITING_FOR_HUMAN_SUPPORT,
            "complete_request": SupportIssueStatus.RESOLVED,
            "fail_request": SupportIssueStatus.FAILED,
        }[result.next_action.value]
        custom_data: dict[str, Any] = {"source_references": [s.model_dump(mode="json") for s in result.sources]}
        if result.clarification_question:
            custom_data["asked_questions"] = [result.clarification_question]
        await self.issues.upsert(request_id, {
            "category": result.category, "product_or_service": result.product_or_service,
            "issue_summary": result.answer[:2000], "symptoms": result.symptoms,
            "error_messages": result.error_messages,
            "troubleshooting_steps": [s.model_dump(mode="json") for s in result.troubleshooting_steps],
            "resolution_summary": result.answer if result.issue_resolved else None,
            "issue_status": status, "requires_it": result.requires_it_collaboration,
            "requires_human_support": result.requires_human_escalation,
            "customer_impact": result.customer_impact, "custom_data": custom_data,
            "resolved_at": datetime.now(UTC) if result.issue_resolved else None,
        })
