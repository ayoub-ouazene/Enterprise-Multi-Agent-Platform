class RouterClientError(Exception):
    """Safe base exception for Router-provider failures."""


class RouterConfigurationError(RouterClientError):
    """Raised when Router functionality is not configured."""


class RouterProviderError(RouterClientError):
    """Raised for sanitized Groq provider failures."""


class RouterOutputError(RouterClientError):
    """Raised when model output remains invalid after correction."""


class CustomerSupportClientError(Exception):
    """Safe base exception for Customer Support model failures."""


class CustomerSupportConfigurationError(CustomerSupportClientError):
    pass


class CustomerSupportProviderError(CustomerSupportClientError):
    pass


class CustomerSupportOutputError(CustomerSupportClientError):
    pass


class ITClientError(Exception):
    """Safe base exception for IT model failures."""


class ITConfigurationError(ITClientError):
    pass


class ITProviderError(ITClientError):
    pass


class ITOutputError(ITClientError):
    pass


class FinanceClientError(Exception):
    """Safe base exception for Finance model failures."""


class FinanceConfigurationError(FinanceClientError):
    pass


class FinanceProviderError(FinanceClientError):
    pass


class FinanceOutputError(FinanceClientError):
    pass


class ProcurementClientError(Exception):
    """Safe base exception for Procurement model failures."""


class ProcurementConfigurationError(ProcurementClientError):
    pass


class ProcurementProviderError(ProcurementClientError):
    pass


class ProcurementOutputError(ProcurementClientError):
    pass
