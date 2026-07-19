from app.departments.it.models import AccessRequest, ITIncident
from app.departments.it.prompt import IT_SYSTEM_PROMPT


def test_it_models_never_store_passwords_or_tokens() -> None:
    columns = {column.name for model in (AccessRequest, ITIncident) for column in model.__table__.columns}
    assert not {"password", "password_hash", "reset_token", "jwt", "api_key"}.intersection(columns)


def test_prompt_prohibits_financial_physical_and_secret_actions() -> None:
    prompt = IT_SYSTEM_PROMPT.lower()
    for phrase in ("never expose passwords", "never approve a budget", "physical", "final supplier"):
        assert phrase in prompt
