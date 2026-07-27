import { describe, expect, it } from 'vitest';
import { ActorType, type OnboardingStatusDetailed } from '../api/types';
import {
  ONBOARDING_STEPS,
  firstIncompleteRoute,
  getNextStepId,
  getPreviousStepId,
  getStepByRequirement,
  isValidStepId,
  stepBlocked,
} from './registry';

const status: OnboardingStatusDetailed = {
  company_id: 'company',
  can_activate: false,
  is_active: false,
  items: [
    { requirement: 'company_profile', satisfied: true, details: null },
    { requirement: 'enabled_departments', satisfied: false, details: 'Required' },
    { requirement: 'employees', satisfied: false, details: 'Required' },
    { requirement: 'managers', satisfied: false, details: 'Required' },
    { requirement: 'policies', satisfied: false, details: 'Required' },
  ],
};

describe('onboarding registry', () => {
  it('defines unique direct routes permitted only to Company accounts', () => {
    expect(new Set(ONBOARDING_STEPS.map((step) => step.route)).size).toBe(ONBOARDING_STEPS.length);
    expect(ONBOARDING_STEPS.every((step) => step.permittedRoles.includes(ActorType.COMPANY))).toBe(true);
  });
  it('maps authoritative readiness keys', () => {
    expect(getStepByRequirement('employees')?.id).toBe('employees');
    expect(firstIncompleteRoute(status)).toBe('/app/onboarding/departments');
  });
  it('validates and navigates nested steps', () => {
    expect(isValidStepId('welcome')).toBe(true);
    expect(isValidStepId('not-a-step')).toBe(false);
    expect(getNextStepId('welcome')).toBe('company');
    expect(getPreviousStepId('employees')).toBe('departments');
  });
  it('blocks dependent future steps using backend completion', () => {
    const managers = ONBOARDING_STEPS.find((step) => step.id === 'managers')!;
    const optional = ONBOARDING_STEPS.find((step) => step.id === 'optional-data')!;
    expect(stepBlocked(managers, status)).toBe(true);
    expect(stepBlocked(optional, status)).toBe(false);
  });
});
