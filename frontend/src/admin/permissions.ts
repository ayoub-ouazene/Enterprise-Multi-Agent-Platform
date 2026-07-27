import type { AuthenticatedUser } from '../api/types';
import { ActorType } from '../api/types';

export type AdminCapability =
  | 'overview'
  | 'company'
  | 'employees'
  | 'managers'
  | 'departments'
  | 'assets'
  | 'software'
  | 'budgets'
  | 'suppliers'
  | 'holidays'
  | 'staffing'
  | 'policies'
  | 'documents'
  | 'failures';

const departmentCapabilities: Record<string, ReadonlySet<AdminCapability>> = {
  it: new Set(['overview', 'employees', 'departments', 'assets', 'software', 'policies', 'documents']),
  finance: new Set(['overview', 'employees', 'departments', 'budgets', 'policies', 'documents']),
  procurement: new Set(['overview', 'employees', 'departments', 'suppliers', 'policies', 'documents']),
  hr: new Set(['overview', 'employees', 'managers', 'departments', 'holidays', 'staffing', 'policies', 'documents']),
  customer_support: new Set(['overview', 'employees', 'departments', 'policies', 'documents']),
};

export function canUseAdminCapability(
  user: AuthenticatedUser | null,
  departmentType: string | null | undefined,
  capability: AdminCapability,
): boolean {
  if (user?.actor_type === ActorType.COMPANY) return true;
  if (user?.actor_type !== ActorType.DEPARTMENT_MANAGER || !user.is_manager) return false;
  return departmentCapabilities[departmentType ?? '']?.has(capability) ?? false;
}

export function canCreateCompanyWideRecords(user: AuthenticatedUser | null): boolean {
  return user?.actor_type === ActorType.COMPANY;
}
