from app.departments.customer_support.models import SupportIssue


def test_support_issue_is_one_to_one_tenant_extension() -> None:
    assert [column.name for column in SupportIssue.__table__.primary_key.columns] == ["request_id"]
    assert SupportIssue.__table__.c.company_id.nullable is False
    assert SupportIssue.__table__.c.troubleshooting_steps.nullable is False
