from app.departments.procurement.prompt import PROCUREMENT_SYSTEM_PROMPT
from app.departments.procurement.schemas import SupplierCandidateResponse


def test_prompt_prohibits_purchase_payment_contract_and_secret_reasoning() -> None:
    prompt = PROCUREMENT_SYSTEM_PROMPT.casefold()
    for phrase in ("never execute", "payment", "contract", "hidden reasoning", "never invent"):
        assert phrase in prompt


def test_public_candidate_schema_excludes_contact_and_custom_metadata() -> None:
    fields = SupplierCandidateResponse.model_fields
    assert "contact_reference" not in fields
    assert "custom_data" not in fields
