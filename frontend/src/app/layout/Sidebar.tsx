import { NavLink } from 'react-router-dom';
import { clsx } from 'clsx';
import type { AuthenticatedUser } from '../../api/types';
import { useDepartments } from '../../api/hooks/useDepartments';
import { Building2, type LucideIcon } from 'lucide-react';
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
      {/* Workspace pill */}
      <div
        className={clsx(
          'mx-3 mb-5 mt-1 flex items-center rounded-2xl border border-white/8 bg-white/5 p-3 backdrop-blur-sm transition-all',
          collapsed ? 'justify-center' : 'gap-3',
        )}
      >
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary-600 to-violet-700 text-white shadow-lg shadow-primary-600/20">
          <Building2 size={18} aria-hidden="true" />
        </span>
        <div
          className={clsx(
            'min-w-0 transition-opacity duration-300',
            collapsed ? 'pointer-events-none w-0 opacity-0' : 'opacity-100',
          )}
        >
          <p className="truncate text-sm font-semibold text-white">Company workspace</p>
          <p className="truncate text-xs text-neutral-700">
            {role}
          </p>
        </div>
      </div>

      {/* Nav groups */}
      <nav aria-label="Main navigation" className="flex-1 space-y-6 px-3">
        {groups.map((group) => (
          <div key={group.label}>
            <p
              className={clsx(
                'mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500 transition-opacity duration-300',
                collapsed && 'h-0 overflow-hidden opacity-0',
              )}
            >
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon as LucideIcon;
                return (
                  <NavLink
                    key={item.href}
                    to={item.href}
                    onClick={onNavigate}
                    title={collapsed ? item.label : undefined}
                    className={({ isActive }) =>
                      clsx(
                        'group relative flex h-10 items-center rounded-xl text-sm font-medium transition-all duration-200',
                        collapsed ? 'justify-center px-2' : 'px-3',
                        isActive
                          ? 'bg-gradient-to-r from-primary-600/20 to-primary-500/10 text-white shadow-[inset_0_1px_0_rgba(99,102,241,0.1)]'
                          : 'text-neutral-700',
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {/* Active accent pill */}
                        <span
                          className={clsx(
                            'absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-full bg-gradient-to-b from-primary-400 to-violet-500 transition-all duration-200',
                            isActive ? 'opacity-100' : 'opacity-0',
                          )}
                        />
                        <Icon
                          size={18}
                          className={clsx(
                            'shrink-0 transition-colors duration-200',
                            isActive
                              ? 'text-primary-400'
                              : 'text-neutral-700',
                          )}
                          aria-hidden="true"
                        />
                        <span
                          className={clsx(
                            'ml-3 truncate transition-opacity duration-200',
                            collapsed && 'pointer-events-none absolute opacity-0',
                          )}
                        >
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

      {/* Mini footer in sidebar */}
      <div
        className={clsx(
          'mx-3 mt-auto mb-3 rounded-2xl border border-white/10 bg-white/5 px-3 py-3 transition-opacity duration-300',
          collapsed && 'opacity-0',
        )}
      >
        <p className="text-[10px] font-medium uppercase tracking-wider text-neutral-600">
          Orchestra v1.0
        </p>
        <p className="mt-0.5 text-[10px] text-neutral-500">
          Enterprise Multi-Agent Platform
        </p>
      </div>
    </div>
  );
}
