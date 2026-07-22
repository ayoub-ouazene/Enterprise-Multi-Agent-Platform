import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.passwords import hash_password
from app.companies.models import Company
from app.core.enums import ActorType, DepartmentType, EmploymentStatus
from app.core.exceptions import (
    BusinessValidationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.departments.models import Department
from app.departments.repository import DepartmentRepository
from app.employees.models import Employee
from app.employees.repository import EmployeeRepository
from app.onboarding.enums import ImportJobStatus, ImportType
from app.onboarding.models import ImportJob
from app.onboarding.parser import ParsedUpload, validate_import_columns
from app.onboarding.repository import ImportJobRepository
from app.onboarding.schemas import (
    ImportConfirmResponse,
    ImportValidateResponse,
    OnboardingStatusItem,
    OnboardingStatusResponse,
    RowValidationResult,
)
from app.onboarding.security import validate_password_strength
from app.rag.enums import KnowledgeDocumentType, KnowledgeIngestionStatus
from app.rag.models import KnowledgeDocument
from app.users.models import User
from app.users.repository import UserRepository

logger = logging.getLogger(__name__)

MANDATORY_IMPORT_TYPES = frozenset({ImportType.EMPLOYEES, ImportType.DEPARTMENTS})


def _normalize_email(value: str) -> str:
    return value.strip().casefold()


def _require_columns(parsed: ParsedUpload, import_type: ImportType) -> None:
    errors = validate_import_columns(import_type.value, parsed.headers)
    if errors:
        raise BusinessValidationError("; ".join(errors))


# ---------------------------------------------------------------------------
# Onboarding status
# ---------------------------------------------------------------------------


class CompanyOnboardingService:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get_status(self) -> OnboardingStatusResponse:
        company = await self.session.scalar(
            select(Company).where(Company.id == self.company_id)
        )
        if company is None:
            raise NotFoundError("Company not found")

        items: list[OnboardingStatusItem] = []

        profile_ok = bool(company.name and company.slug)
        items.append(
            OnboardingStatusItem(
                requirement="company_profile",
                satisfied=profile_ok,
                details=None if profile_ok else "Company name and slug are required",
            )
        )

        dept_result = await self.session.scalars(
            select(Department).where(
                Department.company_id == self.company_id,
                Department.is_active.is_(True),
            )
        )
        departments = list(dept_result.all())
        dept_ok = len(departments) >= 1
        items.append(
            OnboardingStatusItem(
                requirement="enabled_departments",
                satisfied=dept_ok,
                details=f"{len(departments)} department(s) enabled"
                if dept_ok
                else "At least one department must be enabled",
            )
        )

        employee_count = await self.session.scalar(
            select(func.count(Employee.id)).where(
                Employee.company_id == self.company_id,
            )
        ) or 0
        emp_ok = employee_count >= 1
        items.append(
            OnboardingStatusItem(
                requirement="employees",
                satisfied=emp_ok,
                details=f"{employee_count} employee(s)" if emp_ok else "At least one employee is required",
            )
        )

        enabled_types = {d.department_type for d in departments}
        dept_types_with_managers: set[DepartmentType] = set()
        for dept in departments:
            mgr = await self.session.scalar(
                select(Employee).where(
                    Employee.company_id == self.company_id,
                    Employee.department_id == dept.id,
                    Employee.manager_employee_id.isnot(None),
                )
            )
            if mgr is not None:
                dept_types_with_managers.add(dept.department_type)
        missing_mgrs = enabled_types - dept_types_with_managers
        mgr_ok = not missing_mgrs
        items.append(
            OnboardingStatusItem(
                requirement="managers",
                satisfied=mgr_ok,
                details=None
                if mgr_ok
                else f"Missing managers for: {', '.join(sorted(str(t) for t in missing_mgrs))}",
            )
        )

        enabled_dept_scopes = {dt.value for dt in enabled_types}
        policy_result = await self.session.scalars(
            select(KnowledgeDocument).where(
                KnowledgeDocument.company_id == self.company_id,
                KnowledgeDocument.document_type == KnowledgeDocumentType.POLICY,
                KnowledgeDocument.is_active.is_(True),
                KnowledgeDocument.ingestion_status == KnowledgeIngestionStatus.COMPLETED,
            )
        )
        covered_depts: set[str] = set()
        has_shared = False
        for doc in policy_result.all():
            for scope in doc.department_scope:
                if scope.value == "shared":
                    has_shared = True
                covered_depts.add(scope.value)
        policy_ok = has_shared or not (enabled_dept_scopes - covered_depts)
        items.append(
            OnboardingStatusItem(
                requirement="policies",
                satisfied=policy_ok,
                details=None
                if policy_ok
                else "Each enabled department needs an active ingested policy",
            )
        )

        can_activate = all(i.satisfied for i in items) and not company.is_active

        return OnboardingStatusResponse(
            company_id=self.company_id,
            can_activate=can_activate,
            is_active=company.is_active,
            items=items,
        )

    async def activate(self, current_user: AuthenticatedUser) -> None:
        if current_user.actor_type != ActorType.COMPANY:
            raise ForbiddenError("Only company accounts can activate onboarding")

        status = await self.get_status()
        if status.is_active:
            raise BusinessValidationError("Company is already active")
        if not status.can_activate:
            raise BusinessValidationError("Onboarding requirements are not satisfied")

        company = await self.session.scalar(
            select(Company).where(Company.id == self.company_id)
        )
        if company is None:
            raise NotFoundError("Company not found")

        company.is_active = True
        await self.session.flush()
        logger.info(
            "Company %s activated by user %s", self.company_id, current_user.user_id
        )


# ---------------------------------------------------------------------------
# Import service
# ---------------------------------------------------------------------------


class OnboardingImportService:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.job_repo = ImportJobRepository(session, company_id)
        self.user_repo = UserRepository(session, company_id)
        self.employee_repo = EmployeeRepository(session, company_id)
        self.department_repo = DepartmentRepository(session, company_id)

    async def validate_import(
        self,
        import_type: ImportType,
        parsed: ParsedUpload,
        uploaded_by_user_id: UUID,
    ) -> ImportValidateResponse:
        _require_columns(parsed, import_type)

        existing = await self.job_repo.find_existing_completed(
            import_type, parsed.checksum
        )
        if existing is not None:
            raise ConflictError("An identical import was already completed")

        rows, valid_count, invalid_count = await self._validate_rows(
            import_type, parsed.rows
        )

        job = await self.job_repo.create(
            import_type=import_type,
            original_filename=parsed.original_filename,
            uploaded_by_user_id=uploaded_by_user_id,
            checksum=parsed.checksum,
            idempotency_key=parsed.checksum,
            total_rows=len(parsed.rows),
            validation_report={
                "rows": [
                    {
                        "row_number": r.row_number,
                        "status": r.status,
                        "errors": r.errors,
                        "preview": r.preview,
                    }
                    for r in rows
                ]
            },
        )

        status = ImportJobStatus.READY if invalid_count == 0 else ImportJobStatus.FAILED
        if import_type not in MANDATORY_IMPORT_TYPES and valid_count > 0:
            status = ImportJobStatus.READY

        await self.job_repo.update_status(
            job.id,
            status,
            valid_rows=valid_count,
            invalid_rows=invalid_count,
            error_summary=self._build_error_summary(rows) if invalid_count > 0 else None,
        )
        await self.session.commit()
        await self.session.refresh(job)

        can_confirm = import_type not in MANDATORY_IMPORT_TYPES or invalid_count == 0

        return ImportValidateResponse(
            import_job_id=job.id,
            import_type=import_type,
            total_rows=len(parsed.rows),
            valid_rows=valid_count,
            invalid_rows=invalid_count,
            can_confirm=can_confirm,
            rows=rows,
        )

    async def confirm_import(
        self,
        job_id: UUID,
        current_user: AuthenticatedUser,
    ) -> ImportConfirmResponse:
        if current_user.actor_type != ActorType.COMPANY:
            raise ForbiddenError("Only company accounts can confirm imports")

        job = await self.job_repo.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Import job not found")
        if job.status not in (ImportJobStatus.READY, ImportJobStatus.PENDING):
            raise BusinessValidationError(
                f"Import cannot be confirmed from status '{job.status}'"
            )

        await self.job_repo.update_status(job_id, ImportJobStatus.PROCESSING)
        await self.session.commit()

        try:
            report_rows = job.validation_report.get("rows", [])
            valid_rows = [r for r in report_rows if r.get("status") == "valid"]

            if job.import_type == ImportType.EMPLOYEES:
                processed = await self._execute_employee_import(valid_rows)
            elif job.import_type == ImportType.DEPARTMENTS:
                processed = await self._execute_department_import(valid_rows)
            else:
                processed = 0

            final_status = ImportJobStatus.COMPLETED
            await self.job_repo.update_status(
                job_id,
                final_status,
                processed_rows=processed,
            )
            await self.session.commit()

            return ImportConfirmResponse(
                import_job_id=job_id,
                status=final_status,
                processed_rows=processed,
                errors=None,
            )
        except Exception:
            await self.session.rollback()
            await self.job_repo.update_status(
                job_id,
                ImportJobStatus.FAILED,
                error_summary="Execution failed; see server logs",
            )
            await self.session.commit()
            raise

    # -----------------------------------------------------------------------
    # Row validation
    # -----------------------------------------------------------------------

    async def _validate_rows(
        self,
        import_type: ImportType,
        rows: list[dict[str, Any]],
    ) -> tuple[list[RowValidationResult], int, int]:
        if import_type == ImportType.EMPLOYEES:
            return await self._validate_employee_rows(rows)
        if import_type == ImportType.DEPARTMENTS:
            return await self._validate_department_rows(rows)
        results: list[RowValidationResult] = []
        for idx, row in enumerate(rows, start=1):
            results.append(
                RowValidationResult(
                    row_number=idx, status="valid", errors=[], preview=row
                )
            )
        return results, len(results), 0

    async def _validate_employee_rows(
        self,
        rows: list[dict[str, Any]],
    ) -> tuple[list[RowValidationResult], int, int]:
        user_emails = await self.session.scalars(
            select(User.email).where(User.company_id == self.company_id)
        )
        existing_emails = {e.casefold() for e in user_emails.all()}

        emp_codes = await self.session.scalars(
            select(Employee.employee_code).where(
                Employee.company_id == self.company_id
            )
        )
        existing_codes = {c.strip() for c in emp_codes.all()}

        dept_result = await self.session.scalars(
            select(Department).where(Department.company_id == self.company_id)
        )
        dept_map: dict[str, UUID] = {}
        for d in dept_result.all():
            dept_map[d.department_type.value] = d.id
            dept_map[d.name.strip().casefold()] = d.id

        manager_emails_in_file: set[str] = set()
        results: list[RowValidationResult] = []
        valid = 0
        invalid = 0

        for idx, row in enumerate(rows, start=1):
            errors: list[str] = []
            email = _normalize_email(row.get("email", ""))
            if not email:
                errors.append("email is required")
            elif email in existing_emails:
                errors.append("email already exists in this company")
            emp_code = row.get("employee_code", "").strip()
            if not emp_code:
                errors.append("employee_code is required")
            elif emp_code in existing_codes:
                errors.append("employee_code already exists in this company")

            password = row.get("temporary_password", "")
            pw_errors = validate_password_strength(password)
            if pw_errors:
                errors.extend(pw_errors)

            dept_key = row.get("department", "").strip().casefold()
            if dept_key and dept_key not in dept_map:
                errors.append(f"department '{row.get('department')}' not found")

            mgr_email_raw = row.get("manager_email", "").strip()
            if mgr_email_raw:
                manager_emails_in_file.add(_normalize_email(mgr_email_raw))

            if row.get("employment_status", "").strip():
                try:
                    EmploymentStatus(row.get("employment_status").strip().lower())
                except ValueError:
                    errors.append("invalid employment_status")

            # Hash password early for storage in validation report
            password_hash: str | None = None
            if password and not pw_errors:
                try:
                    password_hash = hash_password(password)
                except Exception:
                    errors.append("password hashing failed")

            r = RowValidationResult(
                row_number=idx,
                status="valid" if not errors else "invalid",
                errors=errors,
                preview={
                    "email": email,
                    "employee_code": emp_code,
                    "department": dept_key,
                    "job_title": row.get("job_title", "").strip() or None,
                    "employment_status": row.get("employment_status", "").strip().lower() or "active",
                    "manager_email": _normalize_email(mgr_email_raw) if mgr_email_raw else None,
                    "_password_hash": password_hash,
                },
            )
            results.append(r)
            if errors:
                invalid += 1
            else:
                valid += 1

        # Resolve manager references
        if manager_emails_in_file:
            file_emails = {_normalize_email(r.get("email", "")) for r in rows}
            db_emails = {e.casefold() for e in (await self.session.scalars(
                select(User.email).where(User.company_id == self.company_id)
            )).all()}
            known_emails = file_emails | db_emails
            for r in results:
                mgr_email = r.preview.get("manager_email") if r.preview else None
                if mgr_email and mgr_email not in known_emails:
                    r.errors.append(f"manager_email '{mgr_email}' not found")
                    if r.status == "valid":
                        r.status = "invalid"
                        valid -= 1
                        invalid += 1

        return results, valid, invalid

    async def _validate_department_rows(
        self,
        rows: list[dict[str, Any]],
    ) -> tuple[list[RowValidationResult], int, int]:
        dept_types = await self.session.scalars(
            select(Department.department_type).where(
                Department.company_id == self.company_id
            )
        )
        existing_types = {t for t in dept_types.all()}

        results: list[RowValidationResult] = []
        valid = 0
        invalid = 0
        for idx, row in enumerate(rows, start=1):
            errors: list[str] = []
            dt_raw = row.get("department_type", "").strip().lower()
            if not dt_raw:
                errors.append("department_type is required")
            else:
                try:
                    dt = DepartmentType(dt_raw)
                    if dt in existing_types:
                        errors.append(f"department_type '{dt_raw}' already exists")
                except ValueError:
                    errors.append(
                        f"invalid department_type; allowed: {', '.join(sorted(t.value for t in DepartmentType))}"
                    )
            name = row.get("name", "").strip()
            if not name:
                errors.append("name is required")

            r = RowValidationResult(
                row_number=idx,
                status="valid" if not errors else "invalid",
                errors=errors,
                preview={
                    "department_type": dt_raw,
                    "name": name,
                    "is_active": row.get("is_active", "true").strip().lower()
                    in ("true", "1", "yes", "active"),
                },
            )
            results.append(r)
            if errors:
                invalid += 1
            else:
                valid += 1
        return results, valid, invalid

    # -----------------------------------------------------------------------
    # Execution
    # -----------------------------------------------------------------------

    async def _execute_employee_import(
        self,
        valid_rows: list[dict[str, Any]],
    ) -> int:
        dept_result = await self.session.scalars(
            select(Department).where(Department.company_id == self.company_id)
        )
        dept_map: dict[str, UUID] = {}
        for d in dept_result.all():
            dept_map[d.department_type.value] = d.id
            dept_map[d.name.strip().casefold()] = d.id

        created_employees: dict[str, UUID] = {}
        processed = 0

        for row_data in valid_rows:
            preview = row_data.get("preview", row_data)
            email = preview.get("email", "")
            emp_code = preview.get("employee_code", "")
            dept_key = preview.get("department", "")
            dept_id = dept_map.get(dept_key)
            password_hash = preview.get("_password_hash")

            if not password_hash:
                logger.warning("Missing password hash for row; skipping")
                continue

            user = User(
                id=uuid4(),
                company_id=self.company_id,
                email=email,
                password_hash=password_hash,
                actor_type=ActorType.EMPLOYEE,
                is_active=True,
            )
            self.session.add(user)
            await self.session.flush()

            employee = Employee(
                id=uuid4(),
                company_id=self.company_id,
                user_id=user.id,
                department_id=dept_id,
                employee_code=emp_code,
                job_title=preview.get("job_title"),
                employment_status=EmploymentStatus(
                    preview.get("employment_status", "active")
                ),
                custom_data={},
            )
            self.session.add(employee)
            await self.session.flush()

            created_employees[email] = employee.id
            processed += 1

        # Second pass: resolve manager references
        for row_data in valid_rows:
            preview = row_data.get("preview", row_data)
            email = preview.get("email", "")
            mgr_email = preview.get("manager_email")
            if mgr_email and email in created_employees:
                mgr_id = created_employees.get(mgr_email)
                if mgr_id is None:
                    mgr_user = await self.user_repo.get_by_email(mgr_email)
                    if mgr_user is not None:
                        mgr_emp = await self.employee_repo.get_by_user_id(mgr_user.id)
                        if mgr_emp is not None:
                            mgr_id = mgr_emp.id
                if mgr_id is not None and mgr_id != created_employees[email]:
                    from sqlalchemy import update
                    await self.session.execute(
                        update(Employee)
                        .where(Employee.id == created_employees[email])
                        .values(manager_employee_id=mgr_id)
                    )

        return processed

    async def _execute_department_import(
        self,
        valid_rows: list[dict[str, Any]],
    ) -> int:
        processed = 0
        for row_data in valid_rows:
            preview = row_data.get("preview", row_data)
            dt_raw = preview.get("department_type", "").strip().lower()
            name = preview.get("name", "").strip()
            is_active = preview.get("is_active", True)
            if isinstance(is_active, str):
                is_active = is_active.strip().lower() in ("true", "1", "yes", "active")

            dept_type = DepartmentType(dt_raw)
            existing = await self.department_repo.get_by_type(dept_type)
            if existing is not None:
                await self.department_repo.update(
                    existing.id,
                    {"name": name, "is_active": is_active},
                )
            else:
                await self.department_repo.create(
                    name=name,
                    department_type=dept_type,
                    is_active=is_active,
                    custom_data={},
                )
            processed += 1
        return processed

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _build_error_summary(self, rows: list[RowValidationResult]) -> str:
        error_count = sum(1 for r in rows if r.errors)
        return f"{error_count} of {len(rows)} rows failed validation"


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------


class OnboardingService:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.status_service = CompanyOnboardingService(session, company_id)
        self.import_service = OnboardingImportService(session, company_id)
