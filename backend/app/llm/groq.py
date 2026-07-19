import asyncio
import json
import logging
from enum import StrEnum
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import TYPE_CHECKING, Any

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
    validate_customer_support_configuration,
    validate_it_configuration,
)
from app.llm.exceptions import (
    CustomerSupportConfigurationError,
    CustomerSupportOutputError,
    CustomerSupportProviderError,
    ITConfigurationError,
    ITOutputError,
    ITProviderError,
    RouterConfigurationError,
    RouterOutputError,
    RouterProviderError,
)
if TYPE_CHECKING:
    from app.departments.customer_support.schemas import CustomerSupportModelInput, CustomerSupportResult
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


class SupportModelRole(StrEnum):
    FAST = "fast"
    REASONING = "reasoning"


class GroqCustomerSupportClient:
    """Centralized Groq access for the two approved Customer Support model roles."""

    def __init__(self, settings: Settings, *, client: Any | None = None,
                 sleep: Callable[[float], Awaitable[None]] = asyncio.sleep) -> None:
        try:
            validate_customer_support_configuration(settings)
        except ConfigurationError as exc:
            raise CustomerSupportConfigurationError(str(exc)) from None
        self.settings = settings
        self._sleep = sleep
        self._client = client or AsyncGroq(
            api_key=settings.groq_api_key.get_secret_value(),
            base_url=str(settings.groq_base_url),
            timeout=float(settings.llm_request_timeout_seconds),
            max_retries=0,
        )

    async def generate(
        self, payload: "CustomerSupportModelInput", *, role: SupportModelRole
    ) -> "CustomerSupportResult":
        from app.departments.customer_support.prompt import (
            CUSTOMER_SUPPORT_SYSTEM_PROMPT,
            build_customer_support_user_message,
        )
        from app.departments.customer_support.schemas import CustomerSupportResult
        model = (
            self.settings.groq_model_fast if role == SupportModelRole.FAST
            else self.settings.groq_model_reasoning
        ).strip()
        messages = [
            {"role": "system", "content": CUSTOMER_SUPPORT_SYSTEM_PROMPT},
            {"role": "user", "content": build_customer_support_user_message(payload)},
        ]
        retries = 0
        validation_retry = False
        while True:
            started = monotonic()
            try:
                response = await self._client.chat.completions.create(
                    model=model, messages=messages,
                    temperature=self.settings.llm_temperature,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("empty response")
                result = CustomerSupportResult.model_validate(json.loads(content))
            except TemporaryProviderError:
                self._log_support(started, role, model, retries, "temporary_failure")
                if retries >= self.settings.llm_max_retries:
                    raise CustomerSupportProviderError(
                        "Customer Support is temporarily unavailable"
                    ) from None
                retries += 1
                await self._sleep(min(0.25 * 2 ** (retries - 1), 2.0))
                continue
            except (json.JSONDecodeError, ValidationError, ValueError, IndexError, TypeError):
                self._log_support(started, role, model, retries, "invalid_output")
                if validation_retry or retries >= self.settings.llm_max_retries:
                    raise CustomerSupportOutputError(
                        "Customer Support returned an invalid structured response"
                    ) from None
                validation_retry = True
                retries += 1
                messages.append({
                    "role": "system",
                    "content": "Correct the previous response and return only schema-valid JSON.",
                })
                continue
            except Exception:
                self._log_support(started, role, model, retries, "permanent_failure")
                raise CustomerSupportProviderError("Customer Support request failed") from None
            self._log_support(started, role, model, retries, "success")
            return result

    @staticmethod
    def _log_support(started: float, role: SupportModelRole, model: str,
                     retries: int, category: str) -> None:
        logger.info(
            "LLM request completed role=%s model=%s latency_ms=%d retry_count=%d category=%s",
            f"customer_support_{role.value}", model,
            int((monotonic() - started) * 1000), retries, category,
        )


class GroqITClient:
    """Centralized Groq client for the fixed IT Fast and Reasoning roles."""

    def __init__(self, settings: Settings, *, client: Any | None = None,
                 sleep: Callable[[float], Awaitable[None]] = asyncio.sleep) -> None:
        try:
            validate_it_configuration(settings)
        except ConfigurationError as exc:
            raise ITConfigurationError(str(exc)) from None
        self.settings, self._sleep = settings, sleep
        self._client = client or AsyncGroq(api_key=settings.groq_api_key.get_secret_value(),
            base_url=str(settings.groq_base_url), timeout=float(settings.llm_request_timeout_seconds), max_retries=0)

    async def generate(self, payload: Any, *, role: Any) -> Any:
        from app.departments.it.enums import ITModelRole
        from app.departments.it.prompt import IT_SYSTEM_PROMPT, build_it_user_message
        from app.departments.it.schemas import ITDepartmentResult
        if role not in {ITModelRole.FAST, ITModelRole.REASONING}:
            raise ITConfigurationError("Unsupported IT model role")
        model = (self.settings.groq_model_fast if role == ITModelRole.FAST else self.settings.groq_model_reasoning).strip()
        messages = [{"role": "system", "content": IT_SYSTEM_PROMPT},
            {"role": "user", "content": build_it_user_message(payload)}]
        retries, validation_retry = 0, False
        while True:
            started = monotonic()
            try:
                response = await self._client.chat.completions.create(model=model,
                    messages=messages, temperature=self.settings.llm_temperature,
                    response_format={"type": "json_object"})
                content = response.choices[0].message.content
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("empty response")
                result = ITDepartmentResult.model_validate(json.loads(content))
            except TemporaryProviderError:
                self._log_it(started, role.value, model, retries, "temporary_failure")
                if retries >= self.settings.llm_max_retries:
                    raise ITProviderError("IT is temporarily unavailable") from None
                retries += 1
                await self._sleep(min(0.25 * 2 ** (retries - 1), 2.0))
                continue
            except (json.JSONDecodeError, ValidationError, ValueError, IndexError, TypeError):
                self._log_it(started, role.value, model, retries, "invalid_output")
                if validation_retry or retries >= self.settings.llm_max_retries:
                    raise ITOutputError("IT returned an invalid structured response") from None
                validation_retry, retries = True, retries + 1
                messages.append({"role": "system", "content": "Correct the response and return only valid ITDepartmentResult JSON."})
                continue
            except Exception:
                self._log_it(started, role.value, model, retries, "permanent_failure")
                raise ITProviderError("IT provider request failed") from None
            self._log_it(started, role.value, model, retries, "success")
            return result

    @staticmethod
    def _log_it(started: float, role: str, model: str, retries: int, category: str) -> None:
        logger.info("LLM request completed role=%s model=%s latency_ms=%d retry_count=%d category=%s",
            f"it_{role}", model, int((monotonic() - started) * 1000), retries, category)


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
            except TemporaryProviderError:
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
