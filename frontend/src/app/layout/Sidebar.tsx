import { useLocation } from 'react-router-dom';
import { clsx } from 'clsx';
import type { AuthenticatedUser } from '../../api/types';
import {
  isCompanyAccount,
  isDepartmentManager,
  isEmployee,
  isExternalUser,
  canAccessAdmin,
} from '../../auth/permissions';
import {
  LayoutDashboard,
  ClipboardList,
  Hand,
  Bell,
  Rocket,
  Shield,
  Plus,
} from 'lucide-react';

interface SidebarProps {
  user: AuthenticatedUser | null;
  onNavigate?: () => void;
}

export function Sidebar({ user, onNavigate }: SidebarProps) {
  const location = useLocation();

  if (!user) return null;

  const items = getNavItems(user);

  return (
    <nav aria-label="Main navigation" className="space-y-1 px-3">
      {items.map((item) => {
        const isActive = location.pathname === item.href || location.pathname.startsWith(`${item.href}/`);
        return (
          <a
            key={item.href}
            href={item.href}
            onClick={(e) => {
              e.preventDefault();
              window.history.pushState(null, '', item.href);
              window.dispatchEvent(new PopStateEvent('popstate'));
              onNavigate?.();
            }}
            className={clsx(
              'group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-1',
              isActive
                ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-neutral-200'
            )}
            aria-current={isActive ? 'page' : undefined}
          >
            <span className={clsx(
              'mr-3 flex h-5 w-5 items-center justify-center',
              isActive ? 'text-primary-500 dark:text-primary-400' : 'text-neutral-400 group-hover:text-neutral-500 dark:text-neutral-500 dark:group-hover:text-neutral-400'
            )}>
              {item.icon}
            </span>
            {item.label}
          </a>
        );
      })}
    </nav>
  );
}

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

function getNavItems(user: AuthenticatedUser): NavItem[] {
  const base: NavItem[] = [
    { label: 'Overview', href: '/app/overview', icon: <LayoutDashboard size={18} aria-hidden="true" /> },
  ];

  if (isCompanyAccount(user)) {
    base.push(
      { label: 'Requests', href: '/app/requests', icon: <ClipboardList size={18} aria-hidden="true" /> },
      { label: 'Human Actions', href: '/app/human-actions', icon: <Hand size={18} aria-hidden="true" /> },
      { label: 'Notifications', href: '/app/notifications', icon: <Bell size={18} aria-hidden="true" /> },
      { label: 'Onboarding', href: '/app/onboarding', icon: <Rocket size={18} aria-hidden="true" /> },
      { label: 'Administration', href: '/app/admin', icon: <Shield size={18} aria-hidden="true" /> },
    );
  } else if (isDepartmentManager(user)) {
    base.push(
      { label: 'Requests', href: '/app/requests', icon: <ClipboardList size={18} aria-hidden="true" /> },
      { label: 'Human Actions', href: '/app/human-actions', icon: <Hand size={18} aria-hidden="true" /> },
      { label: 'Notifications', href: '/app/notifications', icon: <Bell size={18} aria-hidden="true" /> },
    );
    if (canAccessAdmin(user)) {
      base.push({ label: 'Administration', href: '/app/admin', icon: <Shield size={18} aria-hidden="true" /> });
    }
  } else if (isEmployee(user) || isExternalUser(user)) {
    base.push(
      { label: 'My Requests', href: '/app/requests', icon: <ClipboardList size={18} aria-hidden="true" /> },
      { label: 'New Request', href: '/app/requests/new', icon: <Plus size={18} aria-hidden="true" /> },
      { label: 'Notifications', href: '/app/notifications', icon: <Bell size={18} aria-hidden="true" /> },
    );
  }

  return base;
}
