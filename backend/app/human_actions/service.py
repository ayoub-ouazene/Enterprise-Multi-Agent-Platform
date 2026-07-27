from datetime import UTC, datetime
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType
from app.core.exceptions import BusinessValidationError, NotFoundError
from app.requests.permissions import can_view_business_request
from app.requests.repository import BusinessRequestRepository
from app.human_actions.models import HumanAction
from app.human_actions.repository import HumanActionRepository
from app.human_actions.schemas import (
    HumanActionCreate,
    HumanActionListFilters,
    HumanActionResponse,
    HumanActionDetailResponse,
    HumanActionSummaryResponse,
    RelatedRequestSummary,
    SafeActionHistoryItem,
    HumanActionSubmitPayload,
    HumanActionSubmitResponse,
)
from app.departments.models import Department


class HumanActionPermissionError(BusinessValidationError):
    pass


class HumanActionService:
    def __init__(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        repository: HumanActionRepository | None = None,
        request_repository: BusinessRequestRepository | None = None,
    ) -> None:
        self.session = session
        self.current_user = current_user
        self.repository = repository or HumanActionRepository(
            session, current_user.company_id
        )
        self.request_repository = request_repository or BusinessRequestRepository(
            session, current_user.company_id
        )

    def _can_view(self, human_action: HumanAction) -> bool:
        if self.current_user.actor_type == ActorType.COMPANY:
            return True
        if human_action.assigned_user_id == self.current_user.user_id:
            return True
        if human_action.assigned_role is not None:
            if (
                self.current_user.actor_type.value == human_action.assigned_role
                or self.current_user.is_manager
            ):
                return True
        # Requesters can view human actions on their own requests
        if human_action.request and human_action.request.requester_user_id == self.current_user.user_id:
            return True
        return False

    def _can_respond(self, human_action: HumanAction) -> bool:
        if human_action.status != "pending":
            return False
        if self.current_user.actor_type in {
            ActorType.COMPANY,
            ActorType.DEPARTMENT_MANAGER,
        }:
            return True
        return human_action.assigned_user_id == self.current_user.user_id

    @staticmethod
    def _allowed_decisions_for(action_type: str) -> list[str]:
        mapping: dict[str, list[str]] = {
            "supplier_selection": ["selected", "rejected"],
            "technician_action": ["completed", "failed", "unable"],
            "onboarding_confirmation": ["completed", "failed", "unable"],
            "information_request": ["submitted", "unable"],
            "identity_verification": ["verified", "rejected", "unable"],
        }
        return mapping.get(action_type, ["approved", "rejected"])

    _COMMON_SAFE_KEYS = {
        "summary", "reason", "impact", "recommendation", "risks",
        "risk_flags", "policy_reference", "policy_summary", "business_reason",
        "requested_action", "expected_result", "safety_note", "diagnostic_steps",
        "subject_reference", "verification_method", "expected_outcome",
        "employee", "employee_name", "leave_type", "start_date", "end_date",
        "workday_count", "current_balance", "projected_balance", "staffing_validation",
        "safe_conflicts", "amount", "currency", "budget", "available_amount",
        "reserved_amount", "committed_amount", "requesting_department",
        "policy_threshold", "finance_recommendation", "supplier", "candidates",
        "shortlist", "rank", "score", "total_cost", "eligible", "eligibility",
        "compliance", "availability", "finance_validation", "score_components",
        "incident", "asset", "system", "issue_summary", "onboarding_step",
        "responsible_department", "requested_resource", "requested_exception",
        "proposed_conditions", "quality_check_summary", "customer_issue",
        "completed_support_steps", "escalation_reason", "requested_fields",
        "options", "deadline", "due_date",
    }
    _NESTED_SAFE_KEYS = {
        "id", "label", "name", "supplier", "rank", "score", "total_cost",
        "currency", "eligible", "eligibility", "reason", "compliance",
        "availability", "finance_validation", "risk_flags", "score_components",
        "value", "title", "description", "required", "helper_text", "field_type",
    }

    @classmethod
    def _safe_context(cls, package: dict) -> dict:
        return {
            key: cls._sanitize_context_value(value)
            for key, value in package.items()
            if key in cls._COMMON_SAFE_KEYS
        }

    @classmethod
    def _sanitize_context_value(cls, value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, list):
            return [cls._sanitize_context_value(item) for item in value[:50]]
        if isinstance(value, dict):
            return {
                key: cls._sanitize_context_value(item)
                for key, item in value.items()
                if key in cls._NESTED_SAFE_KEYS
            }
        return None

    @staticmethod
    def _safe_resolution(action: HumanAction) -> tuple[str | None, str | None]:
        decision = action.response.get("decision")
        raw = action.response.get("response")
        comment = None
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and isinstance(parsed.get("notes"), str):
                    comment = parsed["notes"].strip() or None
            except (TypeError, ValueError):
                comment = raw.strip() or None
        return (
            decision if isinstance(decision, str) else None,
            comment,
        )

    async def _department_name(self, action: HumanAction) -> str | None:
        request = action.request
        department_id = request.active_department_id or request.owner_department_id
        if department_id is None:
            return None
        return await self.session.scalar(
            select(Department.name).where(
                Department.company_id == self.current_user.company_id,
                Department.id == department_id,
            )
        )

    async def _to_summary(self, action: HumanAction) -> HumanActionSummaryResponse:
        request = action.request
        return HumanActionSummaryResponse(
            id=action.id,
            request_id=action.request_id,
            action_type=action.action_type,
            title=action.title,
            status=action.status,
            assigned_role=action.assigned_role,
            due_date=action.due_date,
            resolved_at=action.resolved_at,
            created_at=action.created_at,
            updated_at=action.updated_at,
            allowed_decisions=self._allowed_decisions_for(action.action_type),
            can_respond=self._can_respond(action),
            request_title=request.title if request else None,
            request_status=request.status.value if request else None,
            requesting_department=await self._department_name(action),
        )

    async def _to_detail(self, action: HumanAction) -> HumanActionDetailResponse:
        summary = await self._to_summary(action)
        request = action.request
        decision, comment = self._safe_resolution(action)
        history = [
            SafeActionHistoryItem(
                event="created",
                title="Action created",
                description="The action was assigned for an authorized response.",
                occurred_at=action.created_at,
            )
        ]
        if action.status in {"resolved", "cancelled"}:
            history.append(
                SafeActionHistoryItem(
                    event=action.status,
                    title="Response confirmed" if action.status == "resolved" else "Action cancelled",
                    description="The authoritative action state was updated.",
                    occurred_at=action.resolved_at or action.updated_at,
                )
            )
        return HumanActionDetailResponse(
            **summary.model_dump(),
            description=action.description,
            safe_context=self._safe_context(action.decision_package),
            resolution_decision=decision,
            resolution_comment=comment,
            related_request=RelatedRequestSummary(
                id=request.id,
                title=request.title,
                status=request.status.value,
                owner_department=await self._department_name(action),
            ),
            history=history,
        )

    async def get_public(self, action_id: UUID) -> HumanActionDetailResponse:
        action = await self.repository.get_by_id(action_id)
        if action is None or not self._can_view(action):
            raise NotFoundError("Human action not found")
        return await self._to_detail(action)

    async def list_public(
        self, filters: HumanActionListFilters
    ) -> list[HumanActionSummaryResponse]:
        return [await self._to_summary(item) for item in await self.list_raw(filters)]

    def _to_response(self, human_action: HumanAction) -> HumanActionResponse:
        request_title: str | None = None
        request_status: str | None = None
        if human_action.request is not None:
            request_title = human_action.request.title
            request_status = human_action.request.status.value if hasattr(
                human_action.request.status, "value"
            ) else str(human_action.request.status)
        return HumanActionResponse.model_validate(
            human_action,
            from_attributes=True,
        ).model_copy(update={
            "allowed_decisions": self._allowed_decisions_for(human_action.action_type),
            "can_respond": self._can_respond(human_action),
            "request_title": request_title,
            "request_status": request_status,
        })

    async def get(self, action_id: UUID) -> HumanActionResponse:
        human_action = await self.repository.get_by_id(action_id)
        if human_action is None or not self._can_view(human_action):
            raise NotFoundError("Human action not found")
        return self._to_response(human_action)

    async def list_for_user(self, filters: HumanActionListFilters) -> list[HumanActionResponse]:
        items = await self.list(filters)
        return [self._to_response(item) for item in items]

    async def list_raw(self, filters: HumanActionListFilters) -> list[HumanAction]:
        assigned_user_id: UUID | None = None
        assigned_role: str | None = None

        if self.current_user.actor_type == ActorType.COMPANY:
            pass  # Company can see all
        elif self.current_user.actor_type == ActorType.DEPARTMENT_MANAGER:
            assigned_role = ActorType.DEPARTMENT_MANAGER.value
            assigned_user_id = self.current_user.user_id
        else:
            # Employees/external: see actions assigned to them
            assigned_user_id = self.current_user.user_id

        return await self.repository.list(
            status=filters.status,
            request_id=filters.request_id,
            assigned_user_id=assigned_user_id,
            assigned_role=assigned_role,
            action_type=filters.action_type,
            department_id=filters.department_id,
            due_before=filters.due_before,
            due_after=filters.due_after,
            overdue_only=filters.overdue_only,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def list(self, filters: HumanActionListFilters) -> list[HumanActionResponse]:
        raw_items = await self.list_raw(filters)
        return [self._to_response(item) for item in raw_items]

    async def create(self, payload: HumanActionCreate) -> HumanAction:
        business_request = await self.request_repository.get_by_id(payload.request_id)
        if business_request is None or not can_view_business_request(
            self.current_user, business_request
        ):
            raise NotFoundError("Business request not found")
        if self.current_user.actor_type not in {
            ActorType.COMPANY,
            ActorType.DEPARTMENT_MANAGER,
        }:
            raise HumanActionPermissionError(
                "Only Company accounts or managers can create human actions"
            )

        try:
            human_action = await self.repository.create(
                request_id=payload.request_id,
                action_type=payload.action_type,
                title=payload.title,
                description=payload.description,
                assigned_user_id=payload.assigned_user_id,
                assigned_role=payload.assigned_role,
                decision_package=payload.decision_package,
                due_date=payload.due_date,
            )
            await self.session.commit()
            await self.session.refresh(human_action)
            return human_action
        except Exception:
            await self.session.rollback()
            raise

    async def submit(
        self,
        action_id: UUID,
        payload: HumanActionSubmitPayload,
    ) -> HumanActionSubmitResponse:
        human_action = await self.get(action_id)
        if human_action.status != "pending":
            raise BusinessValidationError(
                "Human action is not in a pending state"
            )
        if self.current_user.actor_type not in {
            ActorType.COMPANY,
            ActorType.DEPARTMENT_MANAGER,
        } and human_action.assigned_user_id != self.current_user.user_id:
            raise HumanActionPermissionError(
                "You are not authorized to submit this action"
            )
        if payload.decision not in self._allowed_decisions_for(human_action.action_type):
            raise BusinessValidationError("Decision is not allowed for this action")

        try:
            updated = await self.repository.submit_response(
                action_id,
                decision=payload.decision,
                response=payload.response,
                responding_user_id=self.current_user.user_id,
                expected_updated_at=payload.expected_updated_at,
            )
            if updated is None:
                raise NotFoundError("Human action not found or already resolved")
            await self.session.commit()
            await self.session.refresh(updated)
            return HumanActionSubmitResponse(
                id=updated.id,
                status=updated.status,
                resolved_at=updated.resolved_at,
            )
        except Exception:
            await self.session.rollback()
            raise
