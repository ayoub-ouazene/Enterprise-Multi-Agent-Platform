import type { ComponentType, SVGProps } from 'react';
import {
  Backpack, Bell, Briefcase, ClipboardList, Hand, LayoutDashboard,
  Plus, Rocket, Shield, Sparkles,
} from 'lucide-react';
import type { AuthenticatedUser, Department } from '../../api/types';
import {
  canAccessAdmin, isCompanyAccount, isDepartmentManager, isEmployee, isExternalUser,
} from '../../auth/permissions';
import { getDepartmentMeta } from '../../lib/departments';

type Icon = ComponentType<SVGProps<SVGSVGElement> & { size?: number | string }>;
export interface NavigationItem { label: string; href: string; icon: Icon; }
export interface NavigationGroup { label: string; items: NavigationItem[]; }

export const SIDEBAR_KEY = 'tellus.sidebar.collapsed';
export const getInitialSidebarCollapsed = () => localStorage.getItem(SIDEBAR_KEY) === 'true';
export const persistSidebarCollapsed = (value: boolean) => localStorage.setItem(SIDEBAR_KEY, String(value));

export function roleLabel(user: AuthenticatedUser): string {
  if (isCompanyAccount(user)) return 'Company account';
  if (isDepartmentManager(user)) return 'Department manager';
  if (isExternalUser(user)) return 'External requester';
  return 'Employee';
}

export function buildNavigation(user: AuthenticatedUser, departments: Department[] = []): NavigationGroup[] {
  const workspace: NavigationItem[] = [
    { label: 'Dashboard', href: '/app/dashboard', icon: LayoutDashboard },
    { label: 'Assistant', href: '/app/assistant', icon: Sparkles },
  ];
  const work: NavigationItem[] = [];
  const manage: NavigationItem[] = [];

  if (isCompanyAccount(user)) {
    work.push(
      { label: 'Requests', href: '/app/requests', icon: ClipboardList },
      { label: 'Human Actions', href: '/app/human-actions', icon: Hand },
      { label: 'Departments', href: '/app/departments', icon: Briefcase },
      { label: 'Notifications', href: '/app/notifications', icon: Bell },
    );
    manage.push(
      { label: 'Onboarding', href: '/app/onboarding', icon: Rocket },
      { label: 'Administration', href: '/app/admin/overview', icon: Shield },
    );
  } else if (isDepartmentManager(user)) {
    work.push(
      { label: 'Requests', href: '/app/requests', icon: ClipboardList },
      { label: 'Human Actions', href: '/app/human-actions', icon: Hand },
      { label: 'Notifications', href: '/app/notifications', icon: Bell },
    );
    const department = departments.find((item) => item.id === user.department_id);
    if (department) {
      const meta = getDepartmentMeta(department.department_type);
      work.push({
        label: meta?.label ?? department.name,
        href: `/app/departments/${meta?.slug ?? department.department_type}/overview`,
        icon: Briefcase,
      });
    }
    if (canAccessAdmin(user)) manage.push({ label: 'Administration', href: '/app/admin/overview', icon: Shield });
  } else if (isEmployee(user) || isExternalUser(user)) {
    workspace.push({ label: 'My Workspace', href: '/app/self-service', icon: Backpack });
    work.push(
      { label: 'My Requests', href: '/app/requests', icon: ClipboardList },
      { label: 'New Request', href: '/app/requests/new', icon: Plus },
      { label: 'Notifications', href: '/app/notifications', icon: Bell },
    );
    if (isEmployee(user)) {
      const department = departments.find((item) => item.id === user.department_id);
      if (department?.is_active) {
        const meta = getDepartmentMeta(department.department_type);
        work.push({
          label: meta?.label ?? department.name,
          href: `/app/departments/${meta?.slug ?? department.department_type}/overview`,
          icon: Briefcase,
        });
      }
    }
  }

  return [
    { label: 'Workspace', items: workspace },
    { label: 'Work', items: work },
    { label: 'Company', items: manage },
  ].filter((group) => group.items.length > 0);
}
