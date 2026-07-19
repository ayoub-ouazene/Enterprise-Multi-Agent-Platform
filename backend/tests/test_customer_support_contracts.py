from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.departments.customer_support.schemas import CustomerSupportResult


def grounded_result(**overrides):
    values = {
        "category": "faq", "answer": "The documented support window is 09:00–17:00.",
        "decision": "answer", "reason": "Authorized FAQ evidence answers the question.",
        "confidence": "high", "sources": [{"document_id": str(uuid4()), "title": "Support FAQ",
        "document_type": "faq", "version": 1, "chunk_index": 0}],
        "next_action": "complete_request", "safe_event_title": "Question answered",
        "safe_event_message": "Customer Support answered from authorized knowledge.",
    }
    values.update(overrides)
    return CustomerSupportResult.model_validate(values)


def test_company_specific_answer_requires_evidence() -> None:
    with pytest.raises(ValidationError, match="require authorized evidence"):
        grounded_result(sources=[])


def test_it_collaboration_is_limited_to_approved_diagnostic_action() -> None:
    with pytest.raises(ValidationError, match="approved IT diagnostic"):
        grounded_result(
            category="technical_issue", decision="prepare_it_collaboration",
            next_action="collaborate", requires_it_collaboration=True,
            it_collaboration_request={"request_id": str(uuid4()),
                "sender_department": "customer_support", "receiver_department": "it",
                "action": "change_account", "payload": {}, "expected_output": {}},
        )
