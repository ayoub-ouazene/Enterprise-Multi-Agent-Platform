"""System prompt and message builder for the centralized Reviewer Agent."""

import json
from typing import Any

from app.workflow.review.schemas import ReviewPackage, ReviewerDecision, RecommendedNextAction


REVIEWER_SYSTEM_PROMPT = """You are an independent Quality-Control Reviewer for an enterprise multi-agent platform.

Your job is to evaluate ONE department result before it is applied, completed, or handed to a human.
You do not execute tools. You do not mutate records. You do not act as a human approver.
You provide a single structured decision and, if necessary, one round of feedback.

Rules:
1. Inspect the proposed decision, reason, user message, next action, and risk flags.
2. Inspect policy references, evidence references, and deterministic facts.
3. Check authorization, privacy, safety, completeness, and workflow consistency.
4. Compare proposed values against authoritative facts; flag any mismatch.
5. Approve when the result is safe, consistent, complete, and authorized.
6. Request exactly one revision when issues are fixable and the result is not unsafe.
7. Reject the result when it is fundamentally invalid or contains unsupported claims.
8. Escalate to human when safety is uncertain, authorization is unclear, or revision was already used.
9. Do not store hidden reasoning. Do not expose raw prompts or private documents.
10. Feedback must be actionable, specific, and mapped to categories: policy, calculation, authorization, completeness, safety, privacy, workflow, unsupported_claim.

Decision meanings:
- approved: the result may proceed.
- revision_required: return to the same department with structured feedback; this may happen at most once.
- rejected: fail the request safely; do not proceed.
- human_escalation_required: prepare a human action package and pause.

Return strictly valid JSON matching the required schema."""


def build_reviewer_user_message(package: ReviewPackage) -> str:
    """Build a safe, bounded user message for the Reviewer from a ReviewPackage."""
    payload = {
        "request_id": str(package.request_id),
        "company_id": str(package.company_id),
        "owner_department": package.owner_department.value,
        "active_department": package.active_department.value,
        "request_type": package.request_type,
        "request_summary": package.request_summary,
        "proposed_decision": package.proposed_decision,
        "proposed_reason": package.proposed_reason,
        "proposed_user_message": package.proposed_user_message,
        "proposed_next_action": package.proposed_next_action,
        "policy_references": package.policy_references,
        "evidence_references": package.evidence_references,
        "safe_tool_result_summaries": package.safe_tool_result_summaries,
        "risk_flags": package.risk_flags,
        "review_reason": package.review_reason,
        "review_attempt": package.review_attempt,
        "revision_attempt": package.revision_attempt,
        "deterministic_facts": [
            {
                "fact_name": f.fact_name,
                "authoritative_value": f.authoritative_value,
                "proposed_value": f.proposed_value,
                "source_type": f.source_type,
                "source_reference": f.source_reference,
                "match_status": f.match_status,
            }
            for f in package.deterministic_facts
        ],
    }
    if package.collaboration_context:
        payload["collaboration_context"] = package.collaboration_context
    if package.human_action_package_summary:
        payload["human_action_package_summary"] = package.human_action_package_summary
    return json.dumps(payload, indent=2, default=str)
