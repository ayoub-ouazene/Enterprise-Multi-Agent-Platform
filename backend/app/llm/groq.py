"""Compatibility shim: old Groq client classes wrapping the unified GroqLLMClient.

All existing imports from ``app.llm.groq`` continue to work; each class is now a
thin adapter over ``GroqLLMClient``.
"""

from __future__ import annotations

from typing import Any, Callable

from app.core.config import Settings
from app.llm.client import GroqLLMClient


class _DepartmentClientMixin:
    """Base mixin that all department-specific clients inherit."""

    _ROLE_NAME: str = "unknown"
    _MODEL_ATTR: str = "groq_model_fast"

    def __init__(
        self,
        settings: Settings,
        *,
        client: Any | None = None,
        sleep: Callable[..., Any] | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {"settings": settings}
        if client is not None:
            kwargs["client"] = client
        self._llm = GroqLLMClient(**kwargs)
        self.settings = settings

    async def generate(
        self,
        payload: Any,
        *,
        role: Any | None = None,
    ) -> Any:
        """Delegate to unified client; return raw dict for backward compat."""
        from app.llm.client import ProviderErrorFactory

        model = getattr(self.settings, self._MODEL_ATTR, self.settings.groq_model_fast)
        return await self._llm.generate(
            messages=[
                {"role": "system", "content": payload.get("system_prompt", "")},
                {"role": "user", "content": payload.get("user_prompt", "")},
            ],
            model=model,
            role_name=self._ROLE_NAME,
            response_schema=payload.get("response_schema"),
            on_provider_error=ProviderErrorFactory,
        )


class GroqRouterClient(_DepartmentClientMixin):
    """Wraps unified client with Router-specific config."""

    _ROLE_NAME = "router"
    _MODEL_ATTR = "groq_model_router"

    def __init__(self, settings: Settings, **kwargs: Any) -> None:
        from app.llm.exceptions import RouterConfigurationError

        if not settings.groq_model_router or not settings.groq_api_key:
            raise RouterConfigurationError("Router not configured")
        super().__init__(settings, **kwargs)
        self.max_retries = settings.llm_max_retries
        self.clarification_maximum = settings.router_max_clarification_questions

    async def classify(self, message: str, **kwargs: Any) -> Any:
        """Router entry-point used by old code."""
        from app.workflow.prompts.router import (
            ROUTER_SYSTEM_PROMPT,
            build_router_user_message,
        )
        from app.workflow.router_output import RouterOutput
        from app.llm.exceptions import RouterProviderError, RouterOutputError

        raw = await self._llm.generate(
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_router_user_message(
                        message=message,
                        clarification_count=kwargs.get("clarification_count", 0),
                        clarification_maximum=self.clarification_maximum,
                        latest_question=kwargs.get("latest_question"),
                        latest_answer=kwargs.get("latest_answer"),
                    ),
                },
            ],
            model=self.settings.groq_model_router,
            response_schema=RouterOutput,
            role_name="router",
            on_provider_error=RouterProviderError,
            on_output_error=RouterOutputError,
        )
        return RouterOutput.model_validate(raw)

    def validate_configuration(self) -> None:
        from app.llm.exceptions import RouterConfigurationError

        if not self.settings.groq_model_router or not self.settings.groq_api_key:
            raise RouterConfigurationError("Router not configured")


class GroqCustomerSupportClient(_DepartmentClientMixin):
    _ROLE_NAME = "customer_support"

    async def generate(self, payload: Any, *, role: Any) -> Any:
        from app.departments.customer_support.schemas import CustomerSupportResult
        from app.llm.exceptions import (
            CustomerSupportProviderError,
            CustomerSupportOutputError,
        )

        raw = await self._llm.generate(
            messages=[
                {"role": "system", "content": payload.get("system_prompt", "")},
                {"role": "user", "content": payload.get("user_prompt", "")},
            ],
            model=self.settings.groq_model_fast if role.value == "fast" else self.settings.groq_model_reasoning,
            response_schema=CustomerSupportResult,
            role_name="customer_support",
            on_provider_error=CustomerSupportProviderError,
            on_output_error=CustomerSupportOutputError,
        )
        return CustomerSupportResult.model_validate(raw)


class GroqITClient(_DepartmentClientMixin):
    _ROLE_NAME = "it"

    async def generate(self, payload: Any, *, role: Any) -> Any:
        from app.departments.it.schemas import ITDepartmentResult
        from app.llm.exceptions import ITProviderError, ITOutputError

        raw = await self._llm.generate(
            messages=[
                {"role": "system", "content": payload.get("system_prompt", "")},
                {"role": "user", "content": payload.get("user_prompt", "")},
            ],
            model=self.settings.groq_model_fast if role.value == "fast" else self.settings.groq_model_reasoning,
            response_schema=ITDepartmentResult,
            role_name="it",
            on_provider_error=ITProviderError,
            on_output_error=ITOutputError,
        )
        return ITDepartmentResult.model_validate(raw)


class GroqFinanceClient(_DepartmentClientMixin):
    _ROLE_NAME = "finance"

    async def generate(self, payload: Any, *, role: Any) -> Any:
        from app.departments.finance.schemas import FinanceDepartmentResult
        from app.llm.exceptions import FinanceProviderError, FinanceOutputError

        raw = await self._llm.generate(
            messages=[
                {"role": "system", "content": payload.get("system_prompt", "")},
                {"role": "user", "content": payload.get("user_prompt", "")},
            ],
            model=self.settings.groq_model_fast if role.value == "fast" else self.settings.groq_model_reasoning,
            response_schema=FinanceDepartmentResult,
            role_name="finance",
            on_provider_error=FinanceProviderError,
            on_output_error=FinanceOutputError,
        )
        return FinanceDepartmentResult.model_validate(raw)


class GroqProcurementClient(_DepartmentClientMixin):
    _ROLE_NAME = "procurement"

    async def generate(self, payload: Any, *, role: Any) -> Any:
        from app.departments.procurement.schemas import ProcurementDepartmentResult
        from app.llm.exceptions import ProcurementProviderError, ProcurementOutputError

        raw = await self._llm.generate(
            messages=[
                {"role": "system", "content": payload.get("system_prompt", "")},
                {"role": "user", "content": payload.get("user_prompt", "")},
            ],
            model=self.settings.groq_model_fast if role.value == "fast" else self.settings.groq_model_reasoning,
            response_schema=ProcurementDepartmentResult,
            role_name="procurement",
            on_provider_error=ProcurementProviderError,
            on_output_error=ProcurementOutputError,
        )
        return ProcurementDepartmentResult.model_validate(raw)


class GroqHRClient(_DepartmentClientMixin):
    _ROLE_NAME = "hr"

    async def generate(self, payload: Any, *, role: Any) -> Any:
        from app.departments.hr.schemas import HRDepartmentResult
        from app.llm.exceptions import HRProviderError, HROutputError

        raw = await self._llm.generate(
            messages=[
                {"role": "system", "content": payload.get("system_prompt", "")},
                {"role": "user", "content": payload.get("user_prompt", "")},
            ],
            model=self.settings.groq_model_fast if role.value == "fast" else self.settings.groq_model_reasoning,
            response_schema=HRDepartmentResult,
            role_name="hr",
            on_provider_error=HRProviderError,
            on_output_error=HROutputError,
        )
        return HRDepartmentResult.model_validate(raw)


class GroqReviewerClient(_DepartmentClientMixin):
    _ROLE_NAME = "reviewer"
    _MODEL_ATTR = "groq_model_reviewer"

    async def review(self, package: Any) -> Any:
        from app.workflow.prompts.reviewer import (
            REVIEWER_SYSTEM_PROMPT,
            build_reviewer_user_message,
        )
        from app.workflow.review.schemas import ReviewerResult
        from app.llm.exceptions import ReviewerProviderError, ReviewerOutputError

        raw = await self._llm.generate(
            messages=[
                {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
                {"role": "user", "content": build_reviewer_user_message(package)},
            ],
            model=self.settings.groq_model_reviewer,
            response_schema=ReviewerResult,
            role_name="reviewer",
            on_provider_error=ReviewerProviderError,
            on_output_error=ReviewerOutputError,
        )
        return ReviewerResult.model_validate(raw)


# Provide SupportModelRole for backward compat
from enum import StrEnum


class SupportModelRole(StrEnum):
    FAST = "fast"
    REASONING = "reasoning"
