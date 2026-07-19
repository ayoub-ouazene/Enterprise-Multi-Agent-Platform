from enum import StrEnum


class CustomerSupportCategory(StrEnum):
    FAQ = "faq"
    PRODUCT_INFORMATION = "product_information"
    SERVICE_INFORMATION = "service_information"
    POLICY_EXPLANATION = "policy_explanation"
    TROUBLESHOOTING = "troubleshooting"
    TECHNICAL_ISSUE = "technical_issue"
    HUMAN_ESCALATION = "human_escalation"
    UNSUPPORTED = "unsupported"


class CustomerSupportDecision(StrEnum):
    ANSWER = "answer"
    TROUBLESHOOT = "troubleshoot"
    CLARIFY = "clarify"
    PREPARE_IT_COLLABORATION = "prepare_it_collaboration"
    PREPARE_HUMAN_ESCALATION = "prepare_human_escalation"
    UNSUPPORTED = "unsupported"


class SupportIssueStatus(StrEnum):
    NEW = "new"
    DIAGNOSING = "diagnosing"
    WAITING_FOR_CUSTOMER = "waiting_for_customer"
    WAITING_FOR_IT = "waiting_for_it"
    WAITING_FOR_HUMAN_SUPPORT = "waiting_for_human_support"
    RESOLVED = "resolved"
    CLOSED = "closed"
    FAILED = "failed"
