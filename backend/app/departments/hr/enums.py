from enum import StrEnum


class HRRequestCategory(StrEnum):
    HR_INFORMATION = "hr_information"
    LEAVE_REQUEST = "leave_request"
    VACATION_REQUEST = "vacation_request"
    LEAVE_BALANCE = "leave_balance"
    BENEFITS_INFORMATION = "benefits_information"
    ONBOARDING = "onboarding"
    JOB_DESCRIPTION = "job_description"
    POLICY_EXCEPTION = "policy_exception"
    MANAGER_APPROVAL_REQUIRED = "manager_approval_required"
    UNSUPPORTED = "unsupported"


class HRDecision(StrEnum):
    INFORMATION_PROVIDED = "information_provided"
    ELIGIBLE = "eligible"
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING_APPROVAL = "pending_approval"
    ONBOARDING_PREPARED = "onboarding_prepared"
    DRAFT_CREATED = "draft_created"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNSUPPORTED = "unsupported"


class HRModelRole(StrEnum):
    FAST = "fast"
    REASONING = "reasoning"


class LeaveType(StrEnum):
    ANNUAL = "annual"
    SICK = "sick"
    UNPAID = "unpaid"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    BEREAVEMENT = "bereavement"
    STUDY = "study"
    OTHER = "other"


class EligibilityStatus(StrEnum):
    PENDING = "pending"
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"


class BalanceStatus(StrEnum):
    PENDING = "pending"
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    NOT_APPLICABLE = "not_applicable"


class StaffingStatus(StrEnum):
    PENDING = "pending"
    SATISFIED = "satisfied"
    CONFLICT = "conflict"
    NOT_APPLICABLE = "not_applicable"


class ApprovalStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LeaveDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class OnboardingStatus(StrEnum):
    PREPARING = "preparing"
    WAITING_FOR_IT = "waiting_for_it"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class JobDescriptionStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    ARCHIVED = "archived"
