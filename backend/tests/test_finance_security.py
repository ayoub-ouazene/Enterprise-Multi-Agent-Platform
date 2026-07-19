from app.departments.finance.models import FinanceRequest, FinancialTransaction
from app.departments.finance.prompt import FINANCE_SYSTEM_PROMPT
from app.departments.finance.schemas import FinancialTransactionResponse


def test_prompt_forbids_supplier_payment_and_secret_actions() -> None:
    lowered = FINANCE_SYSTEM_PROMPT.lower()
    for phrase in ("never choose", "bank transfer", "restricted spending", "credentials"):
        assert phrase in lowered


def test_finance_models_and_public_response_exclude_financial_credentials() -> None:
    prohibited = {"bank_account", "card_number", "password", "api_key", "raw_rag_chunks"}
    model_fields = set(FinanceRequest.__table__.c) | set(FinancialTransaction.__table__.c)
    assert not prohibited.intersection(str(field.name) for field in model_fields)
    assert not prohibited.intersection(FinancialTransactionResponse.model_fields)
