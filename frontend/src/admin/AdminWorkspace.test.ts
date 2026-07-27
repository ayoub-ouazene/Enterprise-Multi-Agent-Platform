import { describe, expect, it } from 'vitest';
import { ActorType, type AuthenticatedUser } from '../api/types';
import { decimalLessThan, formatDecimalMoney } from './decimal';
import { canUseAdminCapability } from './permissions';

function user(actorType: ActorType): AuthenticatedUser {
  return {
    user_id: 'user',
    company_id: 'company',
    email: 'safe@example.com',
    actor_type: actorType,
    employee_id: actorType === ActorType.COMPANY ? null : 'employee',
    department_id: actorType === ActorType.COMPANY ? null : 'department',
    is_manager: actorType === ActorType.DEPARTMENT_MANAGER,
    permissions: [],
    company_active: true,
    onboarding_complete: true,
    must_change_password: false,
  };
}

describe('administration permission presentation', () => {
  it('gives the Company account the approved company-wide sections', () => {
    expect(canUseAdminCapability(user(ActorType.COMPANY), null, 'company')).toBe(true);
    expect(canUseAdminCapability(user(ActorType.COMPANY), null, 'budgets')).toBe(true);
  });

  it('limits department managers to their domain', () => {
    const manager = user(ActorType.DEPARTMENT_MANAGER);
    expect(canUseAdminCapability(manager, 'it', 'assets')).toBe(true);
    expect(canUseAdminCapability(manager, 'it', 'budgets')).toBe(false);
    expect(canUseAdminCapability(manager, 'finance', 'budgets')).toBe(true);
    expect(canUseAdminCapability(manager, 'finance', 'suppliers')).toBe(false);
  });

  it('denies employees and external users', () => {
    expect(canUseAdminCapability(user(ActorType.EMPLOYEE), 'it', 'overview')).toBe(false);
    expect(canUseAdminCapability(user(ActorType.EXTERNAL_USER), null, 'employees')).toBe(false);
  });
});

describe('decimal-safe budget presentation', () => {
  it('formats decimal strings without converting to binary floating point', () => {
    expect(formatDecimalMoney('usd', '1234567890123456.70')).toBe('USD 1,234,567,890,123,456.70');
    expect(decimalLessThan('9999999999999999.99', '10000000000000000.00')).toBe(true);
  });
});
