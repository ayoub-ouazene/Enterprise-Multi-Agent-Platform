/**
 * Onboarding step registry.
 * Maps backend requirement names to UI wizard steps.
 */

export type StepId =
  | 'overview'
  | 'profile'
  | 'departments'
  | 'employees'
  | 'managers'
  | 'policies'
  | 'optional-data'
  | 'review';

export interface StepDef {
  id: StepId;
  label: string;
  description: string;
  requirementKey: string | null; // maps to backend OnboardingStatusItem.requirement; null for non-required
  order: number;
  optional?: boolean;
}

export const ONBOARDING_STEPS: readonly StepDef[] = [
  {
    id: 'overview',
    label: 'Overview',
    description: 'Summary of setup status',
    requirementKey: null,
    order: 0,
  },
  {
    id: 'profile',
    label: 'Company Profile',
    description: 'Name and slug',
    requirementKey: 'company_profile',
    order: 1,
  },
  {
    id: 'departments',
    label: 'Departments',
    description: 'Activate department modules',
    requirementKey: 'enabled_departments',
    order: 2,
  },
  {
    id: 'employees',
    label: 'Employees',
    description: 'Import your team',
    requirementKey: 'employees',
    order: 3,
  },
  {
    id: 'managers',
    label: 'Managers',
    description: 'Assign department leads',
    requirementKey: 'managers',
    order: 4,
  },
  {
    id: 'policies',
    label: 'Policies',
    description: 'Upload department policies',
    requirementKey: 'policies',
    order: 5,
  },
  {
    id: 'optional-data',
    label: 'Optional Data',
    description: 'Assets, budgets, suppliers, etc.',
    requirementKey: null,
    order: 6,
    optional: true,
  },
  {
    id: 'review',
    label: 'Review & Activate',
    description: 'Final checklist and activation',
    requirementKey: null,
    order: 7,
  },
];

export function getStepById(id: StepId): StepDef | undefined {
  return ONBOARDING_STEPS.find((s) => s.id === id);
}

export function getStepByRequirement(key: string): StepDef | undefined {
  return ONBOARDING_STEPS.find((s) => s.requirementKey === key);
}

export function getNextStepId(current: StepId): StepId | null {
  const currentOrder = getStepById(current)?.order ?? -1;
  const next = ONBOARDING_STEPS.find((s) => s.order > currentOrder);
  return next?.id ?? null;
}

export function getPreviousStepId(current: StepId): StepId | null {
  const currentOrder = getStepById(current)?.order ?? -1;
  const prev = [...ONBOARDING_STEPS].reverse().find((s) => s.order < currentOrder);
  return prev?.id ?? null;
}

export function isValidStepId(value: string): value is StepId {
  return ONBOARDING_STEPS.some((s) => s.id === value);
}
