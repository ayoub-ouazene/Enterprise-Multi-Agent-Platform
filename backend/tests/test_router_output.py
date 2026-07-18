import pytest
from pydantic import ValidationError

from app.core.enums import DepartmentType
from app.workflow.router_output import RouterMessageCategory, RouterOutput


def output(**overrides) -> RouterOutput:
    values = {
        "message_category": "business_request",
        "owner_department": "it",
        "confidence": "high",
        "needs_clarification": False,
        "clarification_question": None,
        "platform_answer": None,
        "request_type": "hardware_request",
        "short_summary": "Employee requests a laptop.",
        "routing_reason": "Hardware requests belong to IT.",
        "unsupported_reason": None,
        "is_capability_gap": False,
    }
    values.update(overrides)
    return RouterOutput.model_validate(values)


@pytest.mark.parametrize(
    ("department", "request_type"),
    [
        (DepartmentType.HR, "leave_policy_question"),
        (DepartmentType.IT, "hardware_request"),
        (DepartmentType.FINANCE, "budget_request"),
        (DepartmentType.PROCUREMENT, "supplier_search"),
        (DepartmentType.CUSTOMER_SUPPORT, "customer_problem"),
    ],
)
def test_routed_output_accepts_exactly_one_supported_department(
    department: DepartmentType,
    request_type: str,
) -> None:
    result = output(owner_department=department, request_type=request_type)

    assert result.owner_department == department


def test_platform_question_has_answer_and_no_department() -> None:
    result = output(
        message_category="platform_question",
        owner_department=None,
        platform_answer="The platform supports five departments.",
        request_type=None,
        short_summary=None,
        routing_reason="This asks how the platform works.",
    )

    assert result.message_category == RouterMessageCategory.PLATFORM_QUESTION
    assert result.owner_department is None


def test_unclear_output_requires_one_question() -> None:
    result = output(
        message_category="unclear",
        owner_department=None,
        confidence="low",
        needs_clarification=True,
        clarification_question="Is this your customer account or employee account?",
        request_type=None,
        short_summary=None,
        routing_reason="The account type is ambiguous.",
    )

    assert result.clarification_question.count("?") == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"owner_department": "legal"},
        {"confidence": "certain"},
        {"platform_answer": "A department answer."},
        {"needs_clarification": True, "clarification_question": None},
        {
            "message_category": "unclear",
            "owner_department": None,
            "needs_clarification": True,
            "clarification_question": "First? Second?",
            "request_type": None,
            "short_summary": None,
        },
    ],
)
def test_invalid_or_contradictory_output_is_rejected(changes) -> None:
    with pytest.raises(ValidationError):
        output(**changes)


def test_extra_model_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        output(secret_instruction="hidden")
