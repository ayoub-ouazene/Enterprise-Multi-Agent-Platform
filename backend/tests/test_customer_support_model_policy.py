from app.departments.customer_support.model_policy import requires_reasoning_pass
from tests.test_customer_support_contracts import grounded_result


def test_fast_grounded_answer_does_not_use_reasoning_model() -> None:
    assert requires_reasoning_pass(grounded_result()) is False


def test_low_confidence_or_conflicting_evidence_uses_one_reasoning_pass() -> None:
    assert requires_reasoning_pass(grounded_result(confidence="low")) is True
    assert requires_reasoning_pass(grounded_result(evidence_conflict=True)) is True
