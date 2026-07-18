from collections.abc import Collection
from typing import Any


SENSITIVE_KEY_PARTS = (
    "password",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
)

EVENT_PROHIBITED_KEY_PARTS = SENSITIVE_KEY_PARTS + (
    "authorization",
    "database_url",
    "jwt",
    "raw_prompt",
    "raw_tool_output",
    "chain_of_thought",
    "hidden_reasoning",
    "stack_trace",
    "traceback",
)


def validate_safe_json(
    value: Any,
    *,
    path: str = "value",
    forbidden_key_parts: Collection[str] = SENSITIVE_KEY_PARTS,
) -> Any:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            normalized_key = str(key).casefold()
            if any(part in normalized_key for part in forbidden_key_parts):
                raise ValueError(f"{path} contains a forbidden sensitive key")
            validate_safe_json(
                nested_value,
                path=f"{path}.{key}",
                forbidden_key_parts=forbidden_key_parts,
            )
    elif isinstance(value, list):
        for index, nested_value in enumerate(value):
            validate_safe_json(
                nested_value,
                path=f"{path}[{index}]",
                forbidden_key_parts=forbidden_key_parts,
            )
    return value
