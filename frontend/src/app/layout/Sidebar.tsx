import { NavLink } from 'react-router-dom';
import { clsx } from 'clsx';
import type { AuthenticatedUser } from '../../api/types';
import { useDepartments } from '../../api/hooks/useDepartments';
import { Building2 } from 'lucide-react';
import { buildNavigation, roleLabel } from './shell-utils';

interface SidebarProps {
  user: AuthenticatedUser | null;
  collapsed?: boolean;
  onNavigate?: () => void;
}

export function Sidebar({ user, collapsed = false, onNavigate }: SidebarProps) {
  const { data: departments = [] } = useDepartments();
  if (!user) return null;
  const groups = buildNavigation(user, departments);
  const role = roleLabel(user);

  return (
    <div className="flex h-full flex-col">
      <div className={clsx('mx-3 mb-5 flex items-center rounded-xl bg-neutral-100/80 p-3 dark:bg-neutral-800/70', collapsed ? 'justify-center' : 'gap-3')}>
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-600 text-white">
          <Building2 size={18} aria-hidden="true" />
        </span>
        <div className={clsx('min-w-0 transition-opacity duration-ui', collapsed ? 'pointer-events-none w-0 opacity-0' : 'opacity-100')}>
          <p className="truncate text-sm font-semibold text-neutral-900 dark:text-white">Company workspace</p>
          <p className="truncate text-xs text-neutral-500 dark:text-neutral-400">{role}</p>
        </div>
      </div>

      <nav aria-label="Main navigation" className="flex-1 space-y-5 px-3">
        {groups.map((group) => (
          <div key={group.label}>
            <p className={clsx('mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-neutral-400 transition-opacity duration-ui', collapsed && 'h-0 overflow-hidden opacity-0')}>
              {group.label}
            </p>
            <div className="space-y-1">
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.href}
                    to={item.href}
                    onClick={onNavigate}
                    title={collapsed ? item.label : undefined}
                    className={({ isActive }) => clsx(
                      'group relative flex h-10 items-center rounded-lg text-sm font-medium transition-colors duration-ui',
                      collapsed ? 'justify-center px-2' : 'px-3',
                      isActive
                        ? 'bg-primary-50 text-primary-700 dark:bg-primary-950/70 dark:text-primary-300'
                        : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-950 dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-white',
                    )}
                  >
                    {({ isActive }) => (
                      <>
                        <Icon size={18} className={clsx('shrink-0', isActive ? 'text-primary-600 dark:text-primary-400' : 'text-neutral-400')} aria-hidden="true" />
                        <span className={clsx('ml-3 truncate transition-opacity duration-ui', collapsed && 'pointer-events-none absolute opacity-0')}>
                          {item.label}
                        </span>
                      </>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </div>
  );
}
