import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.enums import DepartmentType


class RouterMessageCategory(StrEnum):
    PLATFORM_QUESTION = "platform_question"
    DEPARTMENT_QUESTION = "department_question"
    BUSINESS_REQUEST = "business_request"
    UNCLEAR = "unclear"
    UNSUPPORTED = "unsupported"


class RouterConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


_REQUEST_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,99}$")


class RouterOutput(BaseModel):
    """Strict, semantically validated output accepted from the Router model."""

    model_config = ConfigDict(extra="forbid")

    message_category: RouterMessageCategory
    owner_department: DepartmentType | None
    confidence: RouterConfidence
    needs_clarification: bool
    clarification_question: str | None = Field(default=None, max_length=300)
    platform_answer: str | None = Field(default=None, max_length=2_000)
    request_type: str | None = Field(default=None, max_length=100)
    short_summary: str | None = Field(default=None, max_length=1_000)
    routing_reason: str = Field(min_length=1, max_length=500)
    unsupported_reason: str | None = Field(default=None, max_length=1_000)
    is_capability_gap: bool

    @field_validator(
        "clarification_question",
        "platform_answer",
        "request_type",
        "short_summary",
        "routing_reason",
        "unsupported_reason",
    )
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("request_type")
    @classmethod
    def validate_request_type(cls, value: str | None) -> str | None:
        if value is not None and not _REQUEST_TYPE_PATTERN.fullmatch(value):
            raise ValueError("must be a normalized lowercase identifier")
        return value

    @field_validator("clarification_question")
    @classmethod
    def validate_one_question(cls, value: str | None) -> str | None:
        if value is not None and ("\n" in value or value.count("?") != 1):
            raise ValueError("must contain exactly one concise question")
        return value

    @model_validator(mode="after")
    def validate_semantics(self) -> "RouterOutput":
        category = self.message_category
        if category == RouterMessageCategory.PLATFORM_QUESTION:
            if (
                self.platform_answer is None
                or self.owner_department is not None
                or self.needs_clarification
                or self.clarification_question is not None
                or self.request_type is not None
                or self.short_summary is not None
                or self.unsupported_reason is not None
                or self.is_capability_gap
            ):
                raise ValueError("platform-question fields are contradictory")
            return self

        if self.platform_answer is not None:
            raise ValueError("platform answers are allowed only for platform questions")

        if category == RouterMessageCategory.UNCLEAR:
            if (
                not self.needs_clarification
                or self.clarification_question is None
                or self.owner_department is not None
                or self.request_type is not None
                or self.short_summary is not None
                or self.unsupported_reason is not None
                or self.is_capability_gap
            ):
                raise ValueError("unclear-message fields are contradictory")
            return self

        if category == RouterMessageCategory.UNSUPPORTED:
            if (
                self.unsupported_reason is None
                or self.owner_department is not None
                or self.needs_clarification
                or self.clarification_question is not None
            ):
                raise ValueError("unsupported-message fields are contradictory")
            return self

        if category in {
            RouterMessageCategory.DEPARTMENT_QUESTION,
            RouterMessageCategory.BUSINESS_REQUEST,
        }:
            if (
                self.owner_department is None
                or self.needs_clarification
                or self.clarification_question is not None
                or self.request_type is None
                or self.short_summary is None
                or self.unsupported_reason is not None
                or self.is_capability_gap
            ):
                raise ValueError("routed-message fields are contradictory")
            return self

        raise ValueError("unsupported Router category")
