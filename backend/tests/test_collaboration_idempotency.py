from uuid import uuid4

from app.core.enums import DepartmentType
from app.workflow.collaboration.idempotency import (
    build_collaboration_idempotency_key,
    canonical_payload,
)


def test_idempotency_key_uses_canonical_payload_and_route_identity() -> None:
    request_id = uuid4()
    common = {
        "request_id": request_id,
        "sender": DepartmentType.IT,
        "receiver": DepartmentType.FINANCE,
        "action": "validate_it_purchase_budget",
    }
    first = build_collaboration_idempotency_key(
        **common, payload={"currency": "USD", "amount": "10.00"}
    )
    second = build_collaboration_idempotency_key(
        **common, payload={"amount": "10.00", "currency": "USD"}
    )
    changed = build_collaboration_idempotency_key(
        **common, payload={"amount": "11.00", "currency": "USD"}
    )
    assert first == second
    assert first != changed
    assert len(first) == 64
    assert canonical_payload({"b": 2, "a": 1}) == '{"a":1,"b":2}'
