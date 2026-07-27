export enum DepartmentType {
  CUSTOMER_SUPPORT = 'customer_support',
  HR = 'hr',
  IT = 'it',
  FINANCE = 'finance',
  PROCUREMENT = 'procurement',
}

export interface DepartmentSection {
  id: string;
  label: string;
  recordTypes: string[];
  emptyTitle: string;
  emptyDescription: string;
}

export interface DepartmentResourceLink {
  label: string;
  href: string;
  companyOnly?: boolean;
}

export interface DepartmentMeta {
  type: DepartmentType;
  label: string;
  shortLabel: string;
  slug: string;
  icon: 'Headphones' | 'Users' | 'Monitor' | 'Landmark' | 'ShoppingCart';
  description: string;
  color: string;
  lightColor: string;
  darkColor: string;
  sections: DepartmentSection[];
  requestTypes: string[];
  humanActionTypes: string[];
  resourceLinks: DepartmentResourceLink[];
}

export const DEPARTMENT_REGISTRY: Record<DepartmentType, DepartmentMeta> = {
  [DepartmentType.CUSTOMER_SUPPORT]: {
    type: DepartmentType.CUSTOMER_SUPPORT,
    label: 'Customer Support',
    shortLabel: 'Support',
    slug: 'customer-support',
    icon: 'Headphones',
    description: 'Resolve customer questions, guide safe troubleshooting, and coordinate technical or human escalation.',
    color: '#d97706',
    lightColor: '#fffbeb',
    darkColor: '#92400e',
    sections: [
      { id: 'issues', label: 'Support issues', recordTypes: ['support_issue'], emptyTitle: 'No open support issues', emptyDescription: 'New support processes will appear here after the Router creates a business request.' },
    ],
    requestTypes: ['customer_support', 'support_issue', 'technical_issue'],
    humanActionTypes: ['customer_support_escalation', 'information_request'],
    resourceLinks: [{ label: 'Policy readiness', href: '/app/admin/policies' }],
  },
  [DepartmentType.HR]: {
    type: DepartmentType.HR,
    label: 'Human Resources',
    shortLabel: 'HR',
    slug: 'hr',
    icon: 'Users',
    description: 'Coordinate leave, staffing, employee onboarding, benefits policy, and safe job-description drafts.',
    color: '#059669',
    lightColor: '#ecfdf5',
    darkColor: '#065f46',
    sections: [
      { id: 'leave', label: 'Leave work', recordTypes: ['leave_request'], emptyTitle: 'No leave work', emptyDescription: 'Authorized leave requests and deterministic validation state will appear here.' },
      { id: 'onboarding', label: 'Employee onboarding', recordTypes: ['onboarding_case'], emptyTitle: 'No onboarding cases', emptyDescription: 'There are no active employee onboarding cases.' },
      { id: 'job-descriptions', label: 'Job-description drafts', recordTypes: ['job_description'], emptyTitle: 'No approved drafts', emptyDescription: 'Safe stored job-description drafts will appear here.' },
    ],
    requestTypes: ['leave_request', 'employee_onboarding', 'benefits_question', 'job_description'],
    humanActionTypes: ['leave_approval', 'onboarding_confirmation', 'policy_exception'],
    resourceLinks: [
      { label: 'Holiday calendar', href: '/app/admin/holidays' },
      { label: 'Staffing rules', href: '/app/admin/staffing-rules' },
      { label: 'HR policies', href: '/app/admin/policies' },
    ],
  },
  [DepartmentType.IT]: {
    type: DepartmentType.IT,
    label: 'Information Technology',
    shortLabel: 'IT',
    slug: 'it',
    icon: 'Monitor',
    description: 'Diagnose incidents, prepare access and hardware work, and coordinate Finance, Procurement, or technicians.',
    color: '#2563eb',
    lightColor: '#eff6ff',
    darkColor: '#1e40af',
    sections: [
      { id: 'incidents', label: 'Incidents', recordTypes: ['incident'], emptyTitle: 'No active incidents', emptyDescription: 'Diagnosed employee and Customer Support incidents will appear here.' },
      { id: 'access', label: 'Access requests', recordTypes: ['access_request'], emptyTitle: 'No access preparations', emptyDescription: 'There are no access operations awaiting IT work.' },
      { id: 'hardware', label: 'Hardware requests', recordTypes: ['hardware_request'], emptyTitle: 'No hardware work', emptyDescription: 'There are no inventory, Finance, Procurement, or delivery preparations.' },
    ],
    requestTypes: ['it_incident', 'software_access', 'hardware_request', 'account_access'],
    humanActionTypes: ['technician_action', 'identity_verification', 'access_approval', 'physical_action'],
    resourceLinks: [
      { label: 'Asset administration', href: '/app/admin/assets' },
      { label: 'Software catalogue', href: '/app/admin/software' },
      { label: 'IT policies', href: '/app/admin/policies' },
    ],
  },
  [DepartmentType.FINANCE]: {
    type: DepartmentType.FINANCE,
    label: 'Finance',
    shortLabel: 'Finance',
    slug: 'finance',
    icon: 'Landmark',
    description: 'Validate budgets, distinguish reservations and commitments, and record confirmed financial movements.',
    color: '#7c3aed',
    lightColor: '#f5f3ff',
    darkColor: '#5b21b6',
    sections: [
      { id: 'validations', label: 'Finance validations', recordTypes: ['finance_request'], emptyTitle: 'No pending validations', emptyDescription: 'Finance requests and authoritative budget checks will appear here.' },
      { id: 'transactions', label: 'Confirmed transactions', recordTypes: ['financial_transaction'], emptyTitle: 'No confirmed transactions', emptyDescription: 'Immutable confirmed financial summaries will appear here.' },
    ],
    requestTypes: ['finance_validation', 'purchase_validation', 'financial_request'],
    humanActionTypes: ['spending_approval', 'financial_exception'],
    resourceLinks: [
      { label: 'Budget administration', href: '/app/admin/budgets' },
      { label: 'Finance policies', href: '/app/admin/policies' },
    ],
  },
  [DepartmentType.PROCUREMENT]: {
    type: DepartmentType.PROCUREMENT,
    label: 'Procurement',
    shortLabel: 'Procurement',
    slug: 'procurement',
    icon: 'ShoppingCart',
    description: 'Evaluate eligible supplier candidates, compare deterministic scores, and prepare human selection.',
    color: '#db2777',
    lightColor: '#fdf2f8',
    darkColor: '#9d174d',
    sections: [
      { id: 'requests', label: 'Procurement requests', recordTypes: ['procurement_request'], emptyTitle: 'No procurement evaluations', emptyDescription: 'No purchase requirement is currently being evaluated.' },
      { id: 'candidates', label: 'Supplier candidates', recordTypes: ['supplier_candidate'], emptyTitle: 'No candidate shortlist', emptyDescription: 'Candidate comparison begins only after a real procurement request is prepared.' },
    ],
    requestTypes: ['procurement_request', 'supplier_evaluation'],
    humanActionTypes: ['supplier_selection', 'procurement_exception'],
    resourceLinks: [
      { label: 'Supplier administration', href: '/app/admin/suppliers' },
      { label: 'Procurement policies', href: '/app/admin/policies' },
    ],
  },
};

export function getDepartmentMeta(type: string): DepartmentMeta | undefined {
  return DEPARTMENT_REGISTRY[type as DepartmentType];
}

export function getDepartmentLabel(type: string): string {
  return getDepartmentMeta(type)?.label ?? type;
}

export function getDepartmentSlug(type: string): string {
  return getDepartmentMeta(type)?.slug ?? type;
}

export function slugToDepartmentType(slug: string): DepartmentType | undefined {
  return Object.values(DEPARTMENT_REGISTRY).find((meta) => meta.slug === slug)?.type;
}
