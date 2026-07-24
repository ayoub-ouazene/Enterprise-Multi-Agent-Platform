/**
 * Frontend-only action-type registry mapping action type strings
 * to presentation config. Unregistered types fall back to generic
 * approval form with `approved`/`rejected` decisions.
 */
// Action type registry

export interface ActionTypeConfig {
  /** Human-readable label displayed in the UI */
  label: string;
  /** Short description of what this action entails */
  description: string;
  /**
   * Form component used to render the response UI.
   * Receives standard props via ActionFormProps.
   */
  formComponent?: string; // lazy-resolved string key to avoid circular refs
}

const registry: Record<string, ActionTypeConfig> = {
  supplier_selection: {
    label: 'Supplier Selection',
    description: 'Choose a vendor from a curated shortlist or supply your own.',
  },
  technician_action: {
    label: 'Technician Action',
    description: 'Perform or confirm a technical operation.',
  },
  onboarding_confirmation: {
    label: 'Onboarding Confirmation',
    description: 'Confirm successful completion or report issues with onboarding.',
  },
  information_request: {
    label: 'Information Request',
    description: 'Provide missing information or attachments requested by the system.',
  },
  identity_verification: {
    label: 'Identity Verification',
    description: 'Verify or reject user identity evidence.',
  },
};

export function getActionTypeConfig(actionType: string): ActionTypeConfig {
  return (
    registry[actionType] ?? {
      label: actionType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
      description: 'Review the request details and provide your decision.',
    }
  );
}

export function isRegisteredActionType(actionType: string): boolean {
  return actionType in registry;
}
