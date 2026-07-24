import { describe, it, expect } from 'vitest';
import { getActionTypeConfig, isRegisteredActionType } from './registry';

describe('human action registry', () => {
  it('returns registered config for known action types', () => {
    const cfg = getActionTypeConfig('supplier_selection');
    expect(cfg.label).toBe('Supplier Selection');
    expect(cfg.description).toContain('vendor');
  });

  it('returns fallback config for unknown action types', () => {
    const cfg = getActionTypeConfig('unknown_action_type');
    expect(cfg.label).toBe('Unknown Action Type');
    expect(cfg.description).toContain('Review');
  });

  it('capitalizes snake_case unknown types', () => {
    const cfg = getActionTypeConfig('urgent_bug_fix');
    expect(cfg.label).toBe('Urgent Bug Fix');
  });

  it('correctly identifies registered vs unregistered types', () => {
    expect(isRegisteredActionType('supplier_selection')).toBe(true);
    expect(isRegisteredActionType('information_request')).toBe(true);
    expect(isRegisteredActionType('random_type')).toBe(false);
  });
});
