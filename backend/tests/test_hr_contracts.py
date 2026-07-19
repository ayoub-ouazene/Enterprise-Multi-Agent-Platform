from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.departments.hr.schemas import HRDepartmentResult, JobDescriptionDraft


def base_result(**updates):
    values = dict(category="hr_information", decision="information_provided", reason="Grounded answer",
        user_message="See the policy.", confidence="high", sources_used=[], next_action="complete_request",
        safe_event_title="HR answer", safe_event_message="HR answered safely.")
    values.update(updates)
    return values


def test_approved_ineligible_leave_is_rejected() -> None:
    with pytest.raises(ValidationError):
        HRDepartmentResult.model_validate(base_result(category="leave_request", decision="approved", leave_eligible=False))


def test_job_description_only_allowed_for_job_category() -> None:
    draft = JobDescriptionDraft(title="Engineer", department_id=uuid4(), employment_type="full_time",
        summary="Build systems", responsibilities=["Build services"], required_skills=["Python"],
        preferred_skills=["PostgreSQL"], experience_level="mid")
    with pytest.raises(ValidationError):
        HRDepartmentResult.model_validate(base_result(job_description=draft.model_dump(mode="json")))


def test_clarification_must_be_one_question() -> None:
    with pytest.raises(ValidationError):
        HRDepartmentResult.model_validate(base_result(needs_user_clarification=True,
            clarification_question="Which type? Which date?", next_action="wait_for_user_input"))
