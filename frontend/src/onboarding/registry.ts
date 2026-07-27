import { ActorType, type OnboardingStatusDetailed } from '../api/types';

export type StepId = 'welcome' | 'company' | 'departments' | 'employees' | 'managers' | 'policies' | 'optional-data' | 'review';

export interface OnboardingStep {
  id: StepId;
  route: string;
  label: string;
  description: string;
  required: boolean;
  readinessKey: string | null;
  dependencies: StepId[];
  permittedRoles: ActorType[];
}

export const ONBOARDING_STEPS: readonly OnboardingStep[] = [
  { id: 'welcome', route: '/app/onboarding/welcome', label: 'Welcome', description: 'Understand the setup journey', required: false, readinessKey: null, dependencies: [], permittedRoles: [ActorType.COMPANY] },
  { id: 'company', route: '/app/onboarding/company', label: 'Company profile', description: 'Confirm workspace identity', required: true, readinessKey: 'company_profile', dependencies: [], permittedRoles: [ActorType.COMPANY] },
  { id: 'departments', route: '/app/onboarding/departments', label: 'Departments', description: 'Enable fixed department modules', required: true, readinessKey: 'enabled_departments', dependencies: ['company'], permittedRoles: [ActorType.COMPANY] },
  { id: 'employees', route: '/app/onboarding/employees', label: 'Employees', description: 'Securely provision employees', required: true, readinessKey: 'employees', dependencies: ['departments'], permittedRoles: [ActorType.COMPANY] },
  { id: 'managers', route: '/app/onboarding/managers', label: 'Managers', description: 'Assign department leadership', required: true, readinessKey: 'managers', dependencies: ['employees'], permittedRoles: [ActorType.COMPANY] },
  { id: 'policies', route: '/app/onboarding/policies', label: 'Policies', description: 'Cover enabled departments', required: true, readinessKey: 'policies', dependencies: ['departments'], permittedRoles: [ActorType.COMPANY] },
  { id: 'optional-data', route: '/app/onboarding/optional-data', label: 'Optional data', description: 'Review operational modules', required: false, readinessKey: null, dependencies: [], permittedRoles: [ActorType.COMPANY] },
  { id: 'review', route: '/app/onboarding/review', label: 'Review & activate', description: 'Resolve blockers and activate', required: false, readinessKey: null, dependencies: ['company', 'departments', 'employees', 'managers', 'policies'], permittedRoles: [ActorType.COMPANY] },
];

export function isValidStepId(value: string | undefined): value is StepId {
  return ONBOARDING_STEPS.some((step) => step.id === value);
}
export function getStepById(id: StepId) { return ONBOARDING_STEPS.find((step) => step.id === id); }
export function getStepByRequirement(key: string) { return ONBOARDING_STEPS.find((step) => step.readinessKey === key); }
export function getNextStepId(id: StepId): StepId | null { const index = ONBOARDING_STEPS.findIndex((step) => step.id === id); return ONBOARDING_STEPS[index + 1]?.id ?? null; }
export function getPreviousStepId(id: StepId): StepId | null { const index = ONBOARDING_STEPS.findIndex((step) => step.id === id); return ONBOARDING_STEPS[index - 1]?.id ?? null; }
export function stepComplete(step: OnboardingStep, status: OnboardingStatusDetailed) { return step.readinessKey ? status.items.find((item) => item.requirement === step.readinessKey)?.satisfied === true : false; }
export function stepBlocked(step: OnboardingStep, status: OnboardingStatusDetailed) { return step.dependencies.some((id) => { const dependency = getStepById(id); return dependency ? !stepComplete(dependency, status) : false; }); }
export function firstIncompleteRoute(status: OnboardingStatusDetailed) { return ONBOARDING_STEPS.find((step) => step.required && !stepComplete(step, status))?.route ?? '/app/onboarding/review'; }
