from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.schemas import AssistantMessageRequest, AssistantMessageResponse
from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.llm.groq import GroqRouterClient
from app.requests.schemas import BusinessRequestCreate
from app.requests.service import BusinessRequestService
from app.workflow.router_output import RouterMessageCategory, RouterOutput
from app.workflow.service import WorkflowService


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

        business_request = await self.request_service.create(
            BusinessRequestCreate(
                request_type=output.request_type or "routing_pending",
                title=(output.short_summary or "Request awaiting clarification")[:255],
                summary=payload.message,
            )
        )
        control = await self.workflow_service.start_for_submission(
            business_request.id,
            preclassified_output=output,
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
