from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.assistant.schemas import AssistantMessageRequest, AssistantMessageResponse
from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.llm.groq import GroqRouterClient
from app.requests.schemas import BusinessRequestCreate
from app.requests.service import BusinessRequestService
from app.workflow.router_output import RouterMessageCategory, RouterOutput
from app.workflow.service import WorkflowService
from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionContext, DepartmentNextAction
from app.rag.pinecone import PineconeProvider


class AssistantService:
    def __init__(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        settings: Settings,
        *,
        router_client=None,
        request_service: BusinessRequestService | None = None,
        workflow_service: WorkflowService | None = None,
        pinecone_provider: PineconeProvider | None = None,
    ) -> None:
        self.session = session
        self.current_user = current_user
        self.settings = settings
        self.router_client = (
            router_client
            if router_client is not None
            else GroqRouterClient(settings)
        )
        self.request_service = request_service or BusinessRequestService(
            session,
            current_user,
        )
        self.workflow_service = workflow_service or WorkflowService(
            session,
            current_user,
            settings=settings,
            router_client=self.router_client,
            pinecone_provider=pinecone_provider,
        )

    async def handle(self, payload: AssistantMessageRequest) -> AssistantMessageResponse:
        if payload.request_id is not None:
            control = await self.workflow_service.resume_for_requester(
                payload.request_id,
                clarification_answer=payload.message,
            )
            return AssistantMessageResponse(
                message_category=control.message_category,
                owner_department=control.owner_department,
                request_id=control.request_id,
                request_status=control.status,
                needs_clarification=control.needs_clarification,
                clarification_question=control.clarification_question,
                response=control.response or "The request was updated.",
                request_type=None,
                short_summary=None,
            )

        output = await self.router_client.classify(payload.message)
        if output.message_category == RouterMessageCategory.PLATFORM_QUESTION:
            return self._nonpersistent_response(
                output,
                output.platform_answer or "Platform guidance is unavailable.",
            )
        if (
            output.message_category == RouterMessageCategory.UNSUPPORTED
            and not output.is_capability_gap
        ):
            return self._nonpersistent_response(
                output,
                output.unsupported_reason
                or "This message is not supported by the platform.",
            )

        precomputed = None
        if (
            output.message_category == RouterMessageCategory.DEPARTMENT_QUESTION
            and output.owner_department == DepartmentType.CUSTOMER_SUPPORT
        ):
            request_id = uuid4()
            support = getattr(
                self.workflow_service.department_execution_service,
                "customer_support_service",
                None,
            )
            if support is not None:
                result = await support.execute(
                    DepartmentExecutionContext(
                        request_id=request_id,
                        company_id=self.current_user.company_id,
                        requester_user_id=self.current_user.user_id,
                        requester_employee_id=self.current_user.employee_id,
                        owner_department_type=DepartmentType.CUSTOMER_SUPPORT,
                        active_department_type=DepartmentType.CUSTOMER_SUPPORT,
                        request_type=output.request_type or "customer_support_question",
                        request_summary=payload.message,
                        current_stage="customer_support_analysis",
                    )
                )
                if result.next_action == DepartmentNextAction.COMPLETE_REQUEST:
                    return self._nonpersistent_response(
                        output, self._with_sources(result.user_message, result)
                    )
                precomputed = result.model_dump(mode="json")
            else:
                request_id = None
        else:
            request_id = None

        create_payload = BusinessRequestCreate(
                request_type=output.request_type or "routing_pending",
                title=(output.short_summary or "Request awaiting clarification")[:255],
                summary=payload.message,
            )
        if request_id is None:
            business_request = await self.request_service.create(create_payload)
        else:
            business_request = await self.request_service.create(
                create_payload, request_id=request_id
            )
        if precomputed is None:
            control = await self.workflow_service.start_for_submission(
                business_request.id,
                preclassified_output=output,
            )
        else:
            control = await self.workflow_service.start_for_submission(
                business_request.id,
                preclassified_output=output,
                precomputed_department_result=precomputed,
            )
        return AssistantMessageResponse(
            message_category=control.message_category,
            owner_department=control.owner_department,
            request_id=control.request_id,
            request_status=control.status,
            needs_clarification=control.needs_clarification,
            clarification_question=control.clarification_question,
            response=control.response or "The request entered the workflow.",
            request_type=output.request_type,
            short_summary=output.short_summary,
        )

    @staticmethod
    def _with_sources(message: str, result) -> str:
        data = result.state_updates.execution
        refs = data.department_data.get("sources", []) if data and data.department_data else []
        titles = list(dict.fromkeys(item["title"] for item in refs if item.get("title")))
        return message if not titles else f"{message}\n\nSources: {', '.join(titles)}"

    @staticmethod
    def _nonpersistent_response(
        output: RouterOutput,
        response: str,
    ) -> AssistantMessageResponse:
        return AssistantMessageResponse(
            message_category=output.message_category,
            owner_department=output.owner_department,
            request_id=None,
            request_status=None,
            needs_clarification=output.needs_clarification,
            clarification_question=output.clarification_question,
            response=response,
            request_type=output.request_type,
            short_summary=output.short_summary,
        )
