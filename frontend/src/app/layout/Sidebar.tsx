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
              {
                'bg-primary-50 text-primary-700': isActive,
                'text-gray-700 hover:bg-gray-100 hover:text-gray-900': !isActive,
              }
            )}
            aria-current={isActive ? 'page' : undefined}
          >
            <span className="mr-3 flex h-5 w-5 items-center justify-center text-gray-400 group-hover:text-gray-500">
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
    { label: 'Overview', href: '/app/overview', icon: <HomeIcon /> },
  ];

  if (isCompanyAccount(user)) {
    base.push(
      { label: 'Requests', href: '/app/requests', icon: <RequestIcon /> },
      { label: 'Human Actions', href: '/app/human-actions', icon: <ActionIcon /> },
      { label: 'Notifications', href: '/app/notifications', icon: <BellIcon /> },
      { label: 'Onboarding', href: '/app/onboarding', icon: <OnboardingIcon /> },
      { label: 'Administration', href: '/app/admin', icon: <AdminIcon /> },
    );
  } else if (isDepartmentManager(user)) {
    base.push(
      { label: 'Requests', href: '/app/requests', icon: <RequestIcon /> },
      { label: 'Human Actions', href: '/app/human-actions', icon: <ActionIcon /> },
      { label: 'Notifications', href: '/app/notifications', icon: <BellIcon /> },
    );
    if (canAccessAdmin(user)) {
      base.push({ label: 'Administration', href: '/app/admin', icon: <AdminIcon /> });
    }
  } else if (isEmployee(user) || isExternalUser(user)) {
    base.push(
      { label: 'My Requests', href: '/app/requests', icon: <RequestIcon /> },
      { label: 'New Request', href: '/app/requests/new', icon: <PlusIcon /> },
      { label: 'Notifications', href: '/app/notifications', icon: <BellIcon /> },
    );
  }

  return base;
}

function HomeIcon() {
  return (
    <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
    </svg>
  );
}

function RequestIcon() {
  return (
    <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V19.5a2.25 2.25 0 002.25 2.25h.75m3 .75H15a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08" />
    </svg>
  );
}

function ActionIcon() {
  return (
    <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.05 4.575a1.575 1.575 0 10-3.15 0v3m3.15-3v-1.5a1.575 1.575 0 013.15 0v1.5m-3.15 0l.075 5.925m3.075.75V4.575m0 0a1.575 1.575 0 013.15 0V15M6.9 7.575V12a6.75 6.75 0 006.75 6.75h.75c2.486 0 4.758-1.325 6.027-3.388l1.302-2.216a3.375 3.375 0 00-2.918-5.044H18.75" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
    </svg>
  );
}

function OnboardingIcon() {
  return (
    <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
    </svg>
  );
}

function AdminIcon() {
  return (
    <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12a7.5 7.5 0 0015 0m-15 0a7.5 7.5 0 1115 0m-15 0H3m18 0h-1.5m-3 13.5l-3-3m0 0l-3 3m3-3v6" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  );
}
