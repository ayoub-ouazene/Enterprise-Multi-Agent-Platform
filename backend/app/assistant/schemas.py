from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import DepartmentType
from app.requests.enums import RequestStatus
from app.workflow.router_output import RouterMessageCategory


class AssistantMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=10_000)
    request_id: UUID | None = None

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class AssistantMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_category: RouterMessageCategory
    owner_department: DepartmentType | None
    request_id: UUID | None
    request_status: RequestStatus | None
    needs_clarification: bool
    clarification_question: str | None
    response: str
    request_type: str | None
    short_summary: str | None
