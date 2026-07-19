from app.departments.hr.prompt import HR_SYSTEM_PROMPT


def test_hr_prompt_contains_privacy_and_authority_boundaries() -> None:
    prompt = HR_SYSTEM_PROMPT.casefold()
    for phrase in ("never process payroll", "private employee information", "never invent",
                   "must not guarantee coverage", "hidden reasoning", "another company's data"):
        assert phrase in prompt


def test_hr_prompt_does_not_authorize_it_execution_or_hiring() -> None:
    prompt = HR_SYSTEM_PROMPT.casefold()
    assert "never process payroll" in prompt
    assert "decide hiring" in prompt
    assert "perform it provisioning" in prompt
