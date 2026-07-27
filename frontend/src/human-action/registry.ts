export type RegisteredActionType =
  | 'approval'
  | 'leave_approval'
  | 'finance_purchase_approval'
  | 'spending_approval'
  | 'supplier_selection'
  | 'technician_action'
  | 'information_request'
  | 'identity_verification'
  | 'onboarding_confirmation'
  | 'policy_exception'
  | 'customer_support_escalation';

export interface ActionTypeConfig {
  type: RegisteredActionType | 'generic';
  label: string;
  description: string;
  tone: 'neutral' | 'info' | 'warning';
  consequence: string;
  rejectionCommentRequired: boolean;
  safeFields: readonly string[];
}

const common = ['summary', 'reason', 'impact', 'recommendation', 'risks', 'risk_flags', 'policy_reference', 'deadline'] as const;

const registry: Record<RegisteredActionType, ActionTypeConfig> = {
  approval: config('approval', 'Approval', 'Review the prepared decision and provide an accountable response.', 'Approval authorizes only the next workflow step.', common),
  leave_approval: config('leave_approval', 'Leave approval', 'Review authoritative leave and staffing facts.', 'The backend revalidates balance and staffing before applying the decision.', [...common, 'employee', 'employee_name', 'leave_type', 'start_date', 'end_date', 'workday_count', 'current_balance', 'projected_balance', 'staffing_validation', 'safe_conflicts']),
  finance_purchase_approval: config('finance_purchase_approval', 'Spending approval', 'Review the exact amount and authoritative budget facts.', 'Approval does not execute payment or purchase.', [...common, 'amount', 'currency', 'budget', 'available_amount', 'reserved_amount', 'committed_amount', 'requesting_department', 'business_reason', 'policy_threshold', 'finance_recommendation']),
  spending_approval: config('spending_approval', 'Spending approval', 'Review the exact amount and authoritative budget facts.', 'Approval does not execute payment or purchase.', [...common, 'amount', 'currency', 'budget', 'available_amount', 'reserved_amount', 'committed_amount', 'requesting_department', 'business_reason', 'policy_threshold', 'finance_recommendation']),
  supplier_selection: config('supplier_selection', 'Supplier selection', 'Select one eligible supplier from the validated shortlist.', 'Selection does not execute a purchase or sign a contract.', [...common, 'candidates', 'shortlist']),
  technician_action: config('technician_action', 'Technician task', 'Record the outcome of authorized manual technical work.', 'Do not include credentials, tokens, confidential logs, or raw shell output.', [...common, 'incident', 'asset', 'system', 'issue_summary', 'requested_action', 'expected_result', 'safety_note', 'diagnostic_steps']),
  information_request: config('information_request', 'Information request', 'Provide only the approved information requested.', 'Never provide passwords, API keys, tokens, or other secrets.', [...common, 'requested_fields', 'requested_action']),
  identity_verification: config('identity_verification', 'Identity verification', 'Confirm the approved verification outcome.', 'Do not upload identity documents unless an authorized secure flow is provided.', [...common, 'subject_reference', 'verification_method', 'expected_outcome']),
  onboarding_confirmation: config('onboarding_confirmation', 'Onboarding confirmation', 'Confirm an onboarding step or report why it could not be completed.', 'Completion is recorded only after backend confirmation.', [...common, 'employee', 'employee_name', 'onboarding_step', 'responsible_department', 'requested_action', 'requested_resource', 'expected_result']),
  policy_exception: config('policy_exception', 'Policy-exception review', 'Review the safe exception package and its risks.', 'Approval applies only to this prepared exception.', [...common, 'requested_exception', 'policy_summary', 'business_reason', 'proposed_conditions', 'quality_check_summary']),
  customer_support_escalation: config('customer_support_escalation', 'Support escalation', 'Review the safe escalation summary and requested decision.', 'This action cannot execute refunds, payments, or account changes.', [...common, 'customer_issue', 'completed_support_steps', 'escalation_reason']),
};

function config(type: RegisteredActionType, label: string, description: string, consequence: string, safeFields: readonly string[]): ActionTypeConfig {
  return { type, label, description, consequence, tone: type.includes('approval') || type === 'policy_exception' ? 'warning' : 'info', rejectionCommentRequired: true, safeFields };
}

export function getActionTypeConfig(actionType: string): ActionTypeConfig {
  return registry[actionType as RegisteredActionType] ?? {
    type: 'generic',
    label: 'Authorized action',
    description: 'Review the safe context and provide one of the allowed responses.',
    consequence: 'The workflow continues only after backend confirmation.',
    tone: 'neutral',
    rejectionCommentRequired: true,
    safeFields: common,
  };
}

export function isRegisteredActionType(actionType: string): actionType is RegisteredActionType {
  return actionType in registry;
}
