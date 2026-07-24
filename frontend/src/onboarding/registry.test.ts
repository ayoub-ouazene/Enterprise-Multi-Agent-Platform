import { describe, it, expect } from 'vitest';
import {
  ONBOARDING_STEPS,
  getStepById,
  getStepByRequirement,
  getNextStepId,
  getPreviousStepId,
  isValidStepId,
} from './registry';

describe('onboarding registry', () => {
  it('has unique step orders', () => {
    const orders = ONBOARDING_STEPS.map((s) => s.order);
    expect(new Set(orders).size).toBe(orders.length);
  });

  it('maps requirement keys to correct steps', () => {
    expect(getStepByRequirement('employees')?.id).toBe('employees');
    expect(getStepByRequirement('policies')?.id).toBe('policies');
    expect(getStepByRequirement('nonexistent')).toBeUndefined();
  });

  it('validates step IDs', () => {
    expect(isValidStepId('overview')).toBe(true);
    expect(isValidStepId('employees')).toBe(true);
    expect(isValidStepId('review')).toBe(true);
    expect(isValidStepId('not_a_step')).toBe(false);
  });

  it('navigates next and previous', () => {
    expect(getNextStepId('overview')).toBe('profile');
    expect(getPreviousStepId('employees')).toBe('departments');
    expect(getNextStepId('review')).toBeNull();
    expect(getPreviousStepId('overview')).toBeNull();
  });

  it('optional-data step is marked optional', () => {
    const step = getStepById('optional-data');
    expect(step?.optional).toBe(true);
  });

  it('review and overview have no requirement key', () => {
    expect(getStepById('review')?.requirementKey).toBeNull();
    expect(getStepById('overview')?.requirementKey).toBeNull();
  });
});
