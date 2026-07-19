from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.departments.customer_support.enums import CustomerSupportCategory, SupportIssueStatus
from app.departments.customer_support.models import SupportIssue


class SupportIssueRepository:
    """Tenant-scoped persistence. Transaction control belongs to the caller."""

    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get(self, request_id: UUID, *, for_update: bool = False) -> SupportIssue | None:
        statement = select(SupportIssue).where(
            SupportIssue.request_id == request_id,
            SupportIssue.company_id == self.company_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def upsert(self, request_id: UUID, values: dict[str, object]) -> SupportIssue:
        issue = await self.get(request_id, for_update=True)
        if issue is None:
            issue = SupportIssue(
                request_id=request_id,
                company_id=self.company_id,
                category=values.pop("category", CustomerSupportCategory.UNSUPPORTED),
                issue_summary=values.pop("issue_summary", "Customer Support request"),
                issue_status=values.pop("issue_status", SupportIssueStatus.NEW),
            )
            self.session.add(issue)
        elif "custom_data" in values:
            values["custom_data"] = {**issue.custom_data, **values["custom_data"]}
        for key, value in values.items():
            setattr(issue, key, value)
        await self.session.flush()
        return issue
