from __future__ import annotations

import asyncio
import json
import logging
from time import monotonic
from typing import Any, Callable

from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncGroq,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
    UnprocessableEntityError,
)
from pydantic import BaseModel, ValidationError

from app.core.config import Settings

logger = logging.getLogger(__name__)

_TEMPORARY_ERRORS = (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

_CLIENT_ERRORS = (BadRequestError, NotFoundError, UnprocessableEntityError)

ProviderErrorFactory = Callable[[str], Exception]
OutputErrorFactory   = Callable[[str], Exception]


class GroqLLMClient:
    """One client for every model role."""

    def __init__(
        self,
        settings: Settings,
        *,
        client: AsyncGroq | None = None,
        sleep: Callable[[float], Any] = asyncio.sleep,
    ) -> None:
        self.settings = settings
        self._sleep = sleep
        if client is not None:
            self._client = client
        else:
            self._client = AsyncGroq(
                api_key=settings.groq_api_key.get_secret_value(),
                base_url=str(settings.groq_base_url),
                timeout=float(settings.llm_request_timeout_seconds),
                max_retries=0,
            )

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        *,
        response_schema: type[BaseModel] | None = None,
        temperature: float | None = None,
        role_name: str = "llm",
        on_provider_error: ProviderErrorFactory | None = None,
        on_output_error: OutputErrorFactory | None = None,
    ) -> dict[str, Any]:
        """Call Groq with centralized retry and optional JSON validation."""
        temp = temperature if temperature is not None else self.settings.llm_temperature
        retries = 0
        validation_retry = False
        corrected_messages = list(messages)

        while True:
            started = monotonic()
            try:
                response = await self._client.chat.completions.create(
                    model=model.strip(),
                    messages=corrected_messages,
                    temperature=temp,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("empty LLM response")

                raw = json.loads(content)

                if response_schema is not None:
                    validated = response_schema.model_validate(raw)
                    return validated.model_dump(mode="json")
                return raw

            except _TEMPORARY_ERRORS:
                self._log(started, role_name, model, retries, "temporary_failure")
                if retries >= self.settings.llm_max_retries:
                    msg = "LLM provider is temporarily unavailable"
                    raise self._provider_exc(on_provider_error, msg)
                retries += 1
                await self._sleep(min(0.25 * (2 ** (retries - 1)), 2.0))
                continue

            except (json.JSONDecodeError, ValidationError, ValueError, IndexError, TypeError) as exc:
                self._log(started, role_name, model, retries, "invalid_output")
                reason = str(exc) if str(exc) else "invalid structured output"
                if validation_retry or retries >= self.settings.llm_max_retries:
                    msg = f"LLM returned an invalid structured response ({reason})"
                    raise self._output_exc(on_output_error, msg)
                validation_retry = True
                retries += 1
                corrected_messages.append({
                    "role": "system",
                    "content": (
                        "The previous response was invalid. Return corrected JSON "
                        "matching the required schema exactly with no extra fields."
                    ),
                })
                continue

            except _CLIENT_ERRORS as exc:
                self._log(started, role_name, model, retries, "client_error")
                groq_status = getattr(exc, "status_code", "no_code")
                groq_body = getattr(exc, "body", "no_body")
                logger.error(
                    "Groq client error: type=%s status=%s body=%s message=%s",
                    type(exc).__name__, groq_status, groq_body, str(exc),
                )
                msg = f"LLM request rejected ({type(exc).__name__}): {str(exc)}"
                raise self._provider_exc(on_provider_error, msg) from None

            except APIStatusError as exc:
                self._log(started, role_name, model, retries, "api_status_error")
                code = getattr(exc, "status_code", 0)
                if code == 429:
                    if retries >= self.settings.llm_max_retries:
                        msg = "LLM provider is rate limited"
                        raise self._provider_exc(on_provider_error, msg) from None
                    retries += 1
                    await self._sleep(min(0.25 * (2 ** (retries - 1)), 2.0))
                    continue
                if code >= 500:
                    if retries >= self.settings.llm_max_retries:
                        msg = f"LLM provider internal error ({code})"
                        raise self._provider_exc(on_provider_error, msg) from None
                    retries += 1
                    await self._sleep(min(0.25 * (2 ** (retries - 1)), 2.0))
                    continue
                msg = f"LLM request failed with status {code}"
                raise self._provider_exc(on_provider_error, msg) from None

            except Exception:
                self._log(started, role_name, model, retries, "permanent_failure")
                msg = "LLM request failed unexpectedly"
                raise self._provider_exc(on_provider_error, msg) from None

    async def validate_credentials(self) -> bool:
        """Smoke-test the API key by listing models. Never raises."""
        try:
            await self._client.models.list()
            logger.info("Groq credential validation passed")
            return True
        except Exception as exc:
            logger.error("Groq credential validation failed: %s", exc)
            return False

    @staticmethod
    def _provider_exc(factory: ProviderErrorFactory | None, msg: str) -> Exception:
        if factory is not None:
            return factory(msg)
        return RuntimeError(msg)

    @staticmethod
    def _output_exc(factory: OutputErrorFactory | None, msg: str) -> Exception:
        if factory is not None:
            return factory(msg)
        return RuntimeError(msg)

    @staticmethod
    def _log(
        started: float,
        role: str,
        model: str,
        retries: int,
        category: str,
    ) -> None:
        logger.info(
            "LLM request completed role=%s model=%s latency_ms=%d retry_count=%d category=%s",
            role,
            model,
            int((monotonic() - started) * 1000),
            retries,
            category,
        )
