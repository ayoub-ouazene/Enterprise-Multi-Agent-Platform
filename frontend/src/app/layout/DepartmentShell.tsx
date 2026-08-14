import { clsx } from 'clsx';
import {
  Activity,
  ClipboardList,
  Database,
  Hand,
  Headphones,
  Landmark,
  LayoutDashboard,
  Monitor,
  Settings,
  ShoppingCart,
  Users,
} from 'lucide-react';
import { NavLink, Outlet, useLocation, useParams } from 'react-router-dom';
import { ConnectionStatus } from '../../components/realtime/ConnectionStatus';
import { Breadcrumbs } from '../../components/ui/Breadcrumbs';
import { Button } from '../../components/ui/Button';
import { getDepartmentMeta, slugToDepartmentType } from '../../lib/departments';
import { useDepartmentReadiness } from '../../api/hooks/useDepartments';
import { useAuthContext } from '../../auth/hooks/useAuthContext';
import { ActorType } from '../../api/types';

const icons = { Headphones, Users, Monitor, Landmark, ShoppingCart };
const sections = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'requests', label: 'Requests', icon: ClipboardList },
  { id: 'operations', label: 'Operations', icon: Database },
  { id: 'actions', label: 'HumanActions', icon: Hand },
  { id: 'activity', label: 'Activity', icon: Activity },
];

export function DepartmentShell() {
  const { deptSlug } = useParams<{ deptSlug: string }>();
  const location = useLocation();
  const { user } = useAuthContext();
  const departmentType = deptSlug ? slugToDepartmentType(deptSlug) : undefined;
  const meta = departmentType ? getDepartmentMeta(departmentType) : undefined;
  const readiness = useDepartmentReadiness(departmentType ?? '');
  if (!meta || !deptSlug) return <div className="p-8 text-neutral-500">Unknown department workspace.</div>;
  const Icon = icons[meta.icon];
  const base = `/app/departments/${deptSlug}`;
  const current = location.pathname.split('/').slice(-1)[0] || 'overview';
  const canManage = user?.actor_type === ActorType.COMPANY || user?.actor_type === ActorType.DEPARTMENT_MANAGER;
  const setupWarnings = readiness.data?.items.filter((item) => !item.ready) ?? [];

  return (
    <div className="min-h-full bg-neutral-50 dark:bg-neutral-950">
      <header className="border-b border-neutral-200 bg-indigo-950 text-white dark:border-neutral-800 dark:bg-indigo-950">
        <div className="mx-auto flex max-w-[1600px] flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl" style={{ backgroundColor: meta.lightColor, color: meta.darkColor }}>
              <Icon size={21} aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-300">Department workspace</p>
              <h1 className="truncate text-lg font-semibold text-white">{meta.label}</h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <ConnectionStatus />
            <span className="hidden max-w-xl text-right text-xs text-neutral-300 lg:block">{meta.description}</span>
          </div>
        </div>
        <div className="mx-auto max-w-[1600px] px-4 pb-3 sm:px-6 lg:px-8">
          <Breadcrumbs items={[
            { label: 'Departments', href: '/app/departments' },
            { label: meta.label, href: `${base}/overview` },
            { label: current.replaceAll('-', ' ') },
          ]} />
        </div>
      </header>

      {setupWarnings.length > 0 && (
        <div className="border-b border-warning-200 bg-warning-50 dark:border-warning-900/40 dark:bg-warning-950/20">
          <div className="mx-auto flex max-w-[1600px] items-start gap-3 px-4 py-3 sm:px-6 lg:px-8">
            <Settings size={16} className="mt-0.5 shrink-0 text-warning-600 dark:text-warning-400" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-warning-800 dark:text-warning-200">{setupWarnings.length} workspace setup item{setupWarnings.length !== 1 ? 's' : ''} need attention</p>
              <p className="mt-0.5 text-xs text-warning-700 dark:text-warning-300">
                {setupWarnings.map((w) => w.name).join(' · ')}
              </p>
            </div>
            {canManage && (
              <Button size="sm" variant="secondary" onClick={() => window.location.href = '/app/admin/policies'}>
                Fix setup
              </Button>
            )}
          </div>
        </div>
      )}

      <div className="mx-auto flex max-w-[1600px]">
        <aside className="hidden w-56 shrink-0 border-r border-neutral-200 bg-indigo-950 px-3 py-5 dark:border-neutral-800 dark:bg-indigo-950 md:block">
          <nav aria-label={`${meta.label} workspace navigation`} className="space-y-1">
            {sections.map((item) => <WorkspaceLink key={item.id} base={base} {...item} />)}
          </nav>
          {meta.resourceLinks.length > 0 && canManage && (
            <div className="mt-6 border-t border-neutral-200 pt-4 dark:border-neutral-800">
              <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wide text-neutral-300">Administration</p>
              <nav className="space-y-1">
                {meta.resourceLinks.map((link) => (
                  <a key={link.href} href={link.href} className="flex min-h-10 items-center gap-2 rounded-lg px-3 text-xs font-medium text-neutral-300 hover:bg-white/5 hover:text-white dark:hover:bg-white/5 dark:hover:text-white">
                    <Settings size={14} /> {link.label}
                  </a>
                ))}
              </nav>
            </div>
          )}
        </aside>
        <div className="min-w-0 flex-1">
          <nav aria-label={`${meta.label} mobile workspace navigation`} className="flex overflow-x-auto border-b border-neutral-200 bg-indigo-950 px-2 text-white md:hidden dark:border-neutral-800 dark:bg-indigo-950">
            {sections.map((item) => <WorkspaceLink key={item.id} base={base} compact {...item} />)}
          </nav>
          <div className="p-4 sm:p-6 lg:p-8">
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  );
}

function WorkspaceLink({
  base,
  id,
  label,
  icon: Icon,
  compact = false,
}: {
  base: string;
  id: string;
  label: string;
  icon: typeof LayoutDashboard;
  compact?: boolean;
}) {
  return (
    <NavLink
      to={`${base}/${id}`}
      className={({ isActive }) => clsx(
        'flex min-h-11 items-center gap-2 rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500',
        compact ? 'shrink-0 px-3' : 'px-3',
        isActive
          ? 'bg-primary-700 text-white dark:bg-primary-700 dark:text-white'
          : 'text-neutral-300 hover:bg-slate-800 hover:text-white dark:text-neutral-300 dark:hover:bg-slate-800 dark:hover:text-white',
      )}
    >
      <Icon size={16} aria-hidden="true" />
      {label}
    </NavLink>
  );
}
