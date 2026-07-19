import hashlib
import json
from typing import Any
from uuid import UUID

from app.core.enums import DepartmentType


def canonical_payload(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def build_collaboration_idempotency_key(
    *,
    request_id: UUID,
    sender: DepartmentType,
    receiver: DepartmentType,
    action: str,
    payload: dict[str, Any],
) -> str:
    material = "|".join(
        (
            str(request_id),
            sender.value,
            receiver.value,
            action,
            canonical_payload(payload),
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def collaboration_route_signature(
    sender: DepartmentType,
    receiver: DepartmentType,
    action: str,
) -> str:
    return f"{sender.value}:{receiver.value}:{action}"
