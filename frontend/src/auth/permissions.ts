import type { AuthenticatedUser } from '../api/types';
import { ActorType } from '../api/types';

export function isCompanyAccount(user: AuthenticatedUser | null): boolean {
  return user?.actor_type === ActorType.COMPANY;
}

export function isDepartmentManager(user: AuthenticatedUser | null): boolean {
  return user?.actor_type === ActorType.DEPARTMENT_MANAGER && user.is_manager;
}

export function isEmployee(user: AuthenticatedUser | null): boolean {
  return user?.actor_type === ActorType.EMPLOYEE;
}

export function isExternalUser(user: AuthenticatedUser | null): boolean {
  return user?.actor_type === ActorType.EXTERNAL_USER;
}

export function canManageEmployees(user: AuthenticatedUser | null): boolean {
  if (isCompanyAccount(user)) return true;
  if (isDepartmentManager(user)) {
    return user != null && user.department_id !== null;
  }
  return false;
}

export function canManageDepartment(user: AuthenticatedUser | null): boolean {
  return isDepartmentManager(user);
}

export function canManageAssets(user: AuthenticatedUser | null): boolean {
  if (isCompanyAccount(user)) return true;
  if (isDepartmentManager(user)) {
    // In a real app, check user.department_type === 'IT'
    return true;
  }
  return false;
}

export function canManageBudgets(user: AuthenticatedUser | null): boolean {
  if (isCompanyAccount(user)) return true;
  if (isDepartmentManager(user)) {
    // In a real app, check user.department_type === 'FINANCE'
    return true;
  }
  return false;
}

export function canManageSuppliers(user: AuthenticatedUser | null): boolean {
  if (isCompanyAccount(user)) return true;
  if (isDepartmentManager(user)) {
    // In a real app, check user.department_type === 'PROCUREMENT'
    return true;
  }
  return false;
}

export function canViewHumanActions(user: AuthenticatedUser | null): boolean {
  return !!user;
}

export function canAccessOnboarding(user: AuthenticatedUser | null): boolean {
  return isCompanyAccount(user);
}

export function canAccessAdmin(user: AuthenticatedUser | null): boolean {
  return isCompanyAccount(user) || isDepartmentManager(user);
}

export function isManagerOfDepartment(
  user: AuthenticatedUser | null,
  departmentId: string
): boolean {
  return isDepartmentManager(user) && user?.department_id === departmentId;
}
