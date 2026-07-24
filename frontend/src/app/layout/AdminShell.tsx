import { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  LayoutDashboard,
  Building2,
  Users,
  Star,
  Layers,
  Wrench,
  FileText,
  Wallet,
  Truck,
  Calendar,
  ClipboardList,
  ShieldCheck,
  ChevronRight,
  Menu,
  X,
} from 'lucide-react';


interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { label: 'Overview', href: '/app/admin/overview', icon: <LayoutDashboard size={16} /> },
  { label: 'Company', href: '/app/admin/company', icon: <Building2 size={16} /> },
  { label: 'Employees', href: '/app/admin/employees', icon: <Users size={16} /> },
  { label: 'Managers', href: '/app/admin/managers', icon: <Star size={16} /> },
  { label: 'Departments', href: '/app/admin/departments', icon: <Layers size={16} /> },
  { label: 'Assets', href: '/app/admin/assets', icon: <Wrench size={16} /> },
  { label: 'Software', href: '/app/admin/software', icon: <FileText size={16} /> },
  { label: 'Budgets', href: '/app/admin/budgets', icon: <Wallet size={16} /> },
  { label: 'Suppliers', href: '/app/admin/suppliers', icon: <Truck size={16} /> },
  { label: 'Holidays', href: '/app/admin/holidays', icon: <Calendar size={16} /> },
  { label: 'Staffing', href: '/app/admin/staffing-rules', icon: <ClipboardList size={16} /> },
  { label: 'Policies', href: '/app/admin/policies', icon: <ShieldCheck size={16} /> },
];

function useBreadcrumb() {
  const location = useLocation();
  const parts = location.pathname.replace('/app/admin', '').split('/').filter(Boolean);
  if (parts.length === 0) return [{ label: 'Administration', href: '/app/admin' }];

  const crumbs = [{ label: 'Administration', href: '/app/admin/overview' }];
  const currentItem = navItems.find((i) => i.href === location.pathname);
  if (currentItem && currentItem.href !== '/app/admin/overview') {
    crumbs.push({ label: currentItem.label, href: currentItem.href });
  }
  return crumbs;
}

export function AdminShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const breadcrumbs = useBreadcrumb();

  return (
    <div className="flex h-full flex-col">
      {/* Breadcrumbs + mobile toggle */}
      <div className="flex items-center justify-between border-b border-neutral-200 bg-white px-4 py-2 dark:border-neutral-800 dark:bg-neutral-900">
        <nav aria-label="Breadcrumb" className="flex items-center space-x-1 text-sm">
          {breadcrumbs.map((crumb, idx) => (
            <div key={crumb.href} className="flex items-center">
              {idx > 0 && <ChevronRight size={14} className="mx-1 text-neutral-400" />}
              <button
                onClick={() => navigate(crumb.href)}
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
          onClick={() => setMobileNavOpen(!mobileNavOpen)}
          aria-label="Toggle admin navigation"
        >
          {mobileNavOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Desktop secondary nav */}
        <aside className="hidden w-56 flex-shrink-0 overflow-y-auto border-r border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900 md:block">
          <nav aria-label="Admin navigation" className="space-y-0.5 p-2">
            {navItems.map((item) => {
              const isActive = location.pathname === item.href;
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
        </aside>

        {/* Mobile secondary nav */}
        {mobileNavOpen && (
          <div className="absolute inset-x-0 top-[41px] z-40 border-b border-neutral-200 bg-white shadow-sm md:hidden dark:border-neutral-800 dark:bg-neutral-900">
            <nav aria-label="Admin navigation mobile" className="space-y-0.5 p-2">
              {navItems.map((item) => {
                const isActive = location.pathname === item.href;
                return (
                  <button
                    key={item.href}
                    onClick={() => {
                      navigate(item.href);
                      setMobileNavOpen(false);
                    }}
                    className={clsx(
                      'flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors',
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

        {/* Main content area */}
        <main className="flex-1 overflow-y-auto bg-neutral-50 p-4 dark:bg-neutral-900">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
