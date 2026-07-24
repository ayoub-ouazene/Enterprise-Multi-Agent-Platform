import { useState } from 'react';
import { Outlet, useParams, useLocation, useNavigate } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  LayoutDashboard,
  ClipboardList,
  Hand,
  Activity,
  Settings,
  ChevronRight,
  Menu,
  X,
} from 'lucide-react';
import { getDepartmentMeta, slugToDepartmentType } from '../../lib/departments';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

function useBreadcrumb(deptLabel: string) {
  const location = useLocation();
  const sub = location.pathname.split('/').filter(Boolean);
  // Expected: ['app', 'departments', '<slug>', '<page>']
  const page = sub[3] ?? 'overview';
  const pageLabel = page.charAt(0).toUpperCase() + page.slice(1).replace(/-/g, ' ');
  return [
    { label: 'Departments', href: '/app/departments' },
    { label: deptLabel, href: '#' },
    { label: pageLabel, href: location.pathname },
  ];
}

export function DepartmentShell() {
  const { deptSlug } = useParams<{ deptSlug: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const deptType = deptSlug ? slugToDepartmentType(deptSlug) : undefined;
  const meta = deptType ? getDepartmentMeta(deptType) : undefined;
  const deptLabel = meta?.label ?? deptSlug ?? 'Department';
  const breadcrumbs = useBreadcrumb(deptLabel);

  if (!deptType || !meta) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-neutral-500 dark:text-neutral-400">
        Unknown department
      </div>
    );
  }

  const base = `/app/departments/${deptSlug}`;
  const navItems: NavItem[] = [
    { label: 'Overview', href: `${base}/overview`, icon: <LayoutDashboard size={16} /> },
    { label: 'Requests', href: `${base}/requests`, icon: <ClipboardList size={16} /> },
    { label: 'Actions', href: `${base}/actions`, icon: <Hand size={16} /> },
    { label: 'Activity', href: `${base}/activity`, icon: <Activity size={16} /> },
    { label: 'Settings', href: `${base}/settings`, icon: <Settings size={16} /> },
  ];

  return (
    <div className="flex h-full flex-col">
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-neutral-200 bg-white px-4 py-2 dark:border-neutral-800 dark:bg-neutral-900">
        <nav aria-label="Breadcrumb" className="flex items-center space-x-1 text-sm">
          {breadcrumbs.map((crumb, idx) => (
            <div key={crumb.label} className="flex items-center">
              {idx > 0 && <ChevronRight size={14} className="mx-1 text-neutral-400" />}
              <button
                onClick={() => crumb.href !== '#' && navigate(crumb.href)}
                className={clsx(
                  'hover:text-primary-600 dark:hover:text-primary-400',
                  idx === breadcrumbs.length - 1
                    ? 'font-medium text-neutral-900 dark:text-neutral-100'
                    : 'text-neutral-600 dark:text-neutral-400'
                )}
              >
                {crumb.label}
              </button>
            </div>
          ))}
        </nav>
        <button
          className="rounded-md p-1 text-neutral-500 hover:bg-neutral-100 md:hidden dark:text-neutral-400 dark:hover:bg-neutral-800"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle department navigation"
        >
          {mobileOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Desktop nav */}
        <aside className="hidden w-56 flex-shrink-0 overflow-y-auto border-r border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900 md:block">
          <div className="p-3">
            <div className="mb-3 flex items-center gap-2 rounded-md px-2 py-2" style={{ backgroundColor: meta.lightColor }}>
              <div className="flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold" style={{ backgroundColor: meta.color, color: '#fff' }}>
                {meta.label.charAt(0)}
              </div>
              <span className="text-sm font-semibold" style={{ color: meta.darkColor }}>
                {meta.label}
              </span>
            </div>
            <nav aria-label="Department navigation" className="space-y-0.5">
              {navItems.map((item) => {
                const isActive = location.pathname === item.href || location.pathname.startsWith(`${item.href}/`);
                return (
                  <button
                    key={item.href}
                    onClick={() => navigate(item.href)}
                    className={clsx(
                      'flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500',
                      isActive
                        ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                        : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-neutral-200'
                    )}
                  >
                    <span className={isActive ? 'text-primary-500 dark:text-primary-400' : 'text-neutral-400'}>
                      {item.icon}
                    </span>
                    {item.label}
                  </button>
                );
              })}
            </nav>
          </div>
        </aside>

        {/* Mobile nav */}
        {mobileOpen && (
          <div className="absolute inset-x-0 top-[41px] z-40 border-b border-neutral-200 bg-white shadow-sm md:hidden dark:border-neutral-800 dark:bg-neutral-900">
            <nav aria-label="Department navigation mobile" className="space-y-0.5 p-2">
              {navItems.map((item) => {
                const isActive = location.pathname === item.href;
                return (
                  <button
                    key={item.href}
                    onClick={() => {
                      navigate(item.href);
                      setMobileOpen(false);
                    }}
                    className={clsx(
                      'flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium',
                      isActive
                        ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                        : 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800'
                    )}
                  >
                    {item.icon}
                    {item.label}
                  </button>
                );
              })}
            </nav>
          </div>
        )}

        {/* Content */}
        <main className="flex-1 overflow-y-auto bg-neutral-50 p-4 dark:bg-neutral-900">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
