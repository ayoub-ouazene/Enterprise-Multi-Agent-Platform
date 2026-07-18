import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any

from groq import (
    APIConnectionError,
    APITimeoutError,
    AsyncGroq,
    InternalServerError,
    RateLimitError,
)
from pydantic import ValidationError

from app.core.config import (
    ConfigurationError,
    Settings,
    validate_router_configuration,
)
from app.llm.exceptions import (
    RouterConfigurationError,
    RouterOutputError,
    RouterProviderError,
)
from app.workflow.prompts.router import (
    ROUTER_SYSTEM_PROMPT,
    build_router_user_message,
)
from app.workflow.router_output import RouterOutput


logger = logging.getLogger(__name__)

TemporaryProviderError = (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)


class GroqRouterClient:
    """Centralized, replaceable Groq client for the Router model role."""

    def __init__(
        self,
        settings: Settings,
        *,
        client: Any | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        try:
            validate_router_configuration(settings)
        except ConfigurationError as exc:
            raise RouterConfigurationError(str(exc)) from None

        self.settings = settings
        self.model = settings.groq_model_router.strip()
        self.max_retries = settings.llm_max_retries
        self.clarification_maximum = settings.router_max_clarification_questions
        self._sleep = sleep
        self._client = (
            client
            if client is not None
            else AsyncGroq(
                api_key=settings.groq_api_key.get_secret_value(),
                base_url=str(settings.groq_base_url),
                timeout=float(settings.llm_request_timeout_seconds),
                max_retries=0,
            )
        )

    def validate_configuration(self) -> None:
        """Allow workflow services to validate before mutating a request."""

        try:
            validate_router_configuration(self.settings)
        except ConfigurationError as exc:
            raise RouterConfigurationError(str(exc)) from None

    async def classify(
        self,
        message: str,
        *,
        clarification_count: int = 0,
        latest_question: str | None = None,
        latest_answer: str | None = None,
    ) -> RouterOutput:
        user_message = build_router_user_message(
            message=message,
            clarification_count=clarification_count,
            clarification_maximum=self.clarification_maximum,
            latest_question=latest_question,
            latest_answer=latest_answer,
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        retries_used = 0
        validation_retry_used = False

        while True:
            started = monotonic()
            try:
                response = await self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.settings.llm_temperature,
                    response_format={"type": "json_object"},
                )
                output = self._parse_response(response)
                if (
                    output.needs_clarification
                    and clarification_count >= self.clarification_maximum
                ):
                    raise ValueError("clarification limit was exceeded")
            except TemporaryProviderError as exc:
                self._log_attempt(started, retries_used, "temporary_failure")
                if retries_used >= self.max_retries:
                    raise RouterProviderError(
                        "The Router provider is temporarily unavailable"
                    ) from None
                retries_used += 1
                await self._sleep(min(0.25 * (2 ** (retries_used - 1)), 2.0))
                continue
            except (json.JSONDecodeError, ValidationError, ValueError, IndexError, TypeError):
                self._log_attempt(started, retries_used, "invalid_output")
                if validation_retry_used or retries_used >= self.max_retries:
                    raise RouterOutputError(
                        "The Router returned an invalid structured response"
                    ) from None
                validation_retry_used = True
                retries_used += 1
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "The previous response was invalid. Return a corrected JSON "
                            "object that satisfies every schema and routing rule."
                        ),
                    }
                )
                continue
            except Exception:
                self._log_attempt(started, retries_used, "permanent_failure")
                raise RouterProviderError("The Router provider request failed") from None

            self._log_attempt(started, retries_used, "success")
            return output

    @staticmethod
    def _parse_response(response: Any) -> RouterOutput:
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty Router response")
        raw = json.loads(content)
        return RouterOutput.model_validate(raw)

    def _log_attempt(self, started: float, retry_count: int, category: str) -> None:
        logger.info(
            "LLM request completed role=%s model=%s latency_ms=%d retry_count=%d category=%s",
            "router",
            self.model,
            int((monotonic() - started) * 1_000),
            retry_count,
            category,
        )
