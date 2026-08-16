"""Checkpoint persistence: save workflow state to the database after every step."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.requests.models import BusinessRequest
from app.workflow.simple_state import WorkflowState

logger = logging.getLogger(__name__)


class CheckpointPersistence:
    """Save and load workflow state from the workflow_state JSONB column."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, state: WorkflowState) -> None:
        request_id = state.request.request_id
        data = state.to_dict()

        try:
            stmt = select(BusinessRequest).where(BusinessRequest.id == request_id)
            result = await self.session.execute(stmt)
            business_request = result.scalar_one_or_none()

            if business_request is None:
                logger.error("Checkpoint failed: request %s not found", request_id)
                return

            business_request.workflow_state = data
            business_request.status = state.request.status
            business_request.current_stage = state.request.current_stage
            business_request.updated_at = datetime.now(timezone.utc)

            await self.session.commit()
            logger.debug("Checkpoint saved for request %s", request_id)
        except Exception as exc:
            await self.session.rollback()
            logger.exception("Checkpoint save failed: %s", exc)
            raise

    async def load(self, request_id: UUID) -> WorkflowState | None:
        try:
            stmt = select(BusinessRequest).where(BusinessRequest.id == request_id)
            result = await self.session.execute(stmt)
            business_request = result.scalar_one_or_none()

            if business_request is None:
                return None

            if not business_request.workflow_state:
                from app.workflow.simple_state import RequestSection
                return WorkflowState(
                    state_version=1,
                    request=RequestSection(
                        request_id=business_request.id,
                        company_id=business_request.company_id,
                        requester_user_id=business_request.requester_user_id,
                        requester_employee_id=business_request.requester_employee_id,
                        request_type=business_request.request_type,
                        summary=business_request.summary,
                        status=business_request.status,
                        current_stage=business_request.current_stage,
                    ),
                )

            return WorkflowState.from_dict(business_request.workflow_state)
        except Exception as exc:
            logger.exception("Checkpoint load failed: %s", exc)
            return None
