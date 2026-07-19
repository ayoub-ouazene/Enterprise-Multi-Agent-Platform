from pathlib import Path


def test_hr_migration_has_complete_upgrade_and_downgrade() -> None:
    text = Path("alembic/versions/20260719_0012_hr_foundation.py").read_text(encoding="utf-8")
    assert 'revision: str = "20260719_0012"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260719_0011"' in text
    for table in ("leave_balances", "leave_requests", "company_holidays",
                  "department_staffing_rules", "onboarding_requests", "job_descriptions"):
        assert f'"{table}"' in text
        assert f'op.drop_table("{table}")' in text
    assert 'op.add_column("employees"' in text
    assert 'op.drop_column("employees", "hire_date")' in text
