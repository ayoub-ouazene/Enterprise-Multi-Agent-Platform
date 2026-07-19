from uuid import uuid4

from app.departments.finance.enums import FinanceModelRole
from app.departments.finance.model_policy import initial_model_role, requires_reasoning_pass
from app.departments.finance.schemas import FinanceExecutionInput
from tests.test_finance_contracts import valid_finance_result


def context(request_type: str = "budget_validation") -> FinanceExecutionInput:
    return FinanceExecutionInput(
        request_id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
        requester_actor_type="employee", owner_department_type="finance",
        active_department_type="finance", request_type=request_type,
        original_summary="Validate this budget", current_stage="finance_analysis",
    )


def test_simple_validation_uses_fast_model() -> None:
    assert initial_model_role(context()) == FinanceModelRole.FAST
    assert requires_reasoning_pass(valid_finance_result(), FinanceModelRole.FAST) is False


def test_complex_or_high_risk_work_uses_reasoning() -> None:
    assert initial_model_role(context("multi_budget_validation")) == FinanceModelRole.REASONING
    assert requires_reasoning_pass(
        valid_finance_result(confidence="low"), FinanceModelRole.FAST
    ) is True
