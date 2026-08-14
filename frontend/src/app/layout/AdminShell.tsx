import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  Boxes, Building2, CalendarDays, ChevronRight, CircleDollarSign,
  ClipboardCheck, FileText, Gauge, HardDrive, Menu, PackageSearch,
  ShieldAlert, ShieldCheck, Users, X,
} from 'lucide-react';
import { useAuthContext } from '../../auth/hooks/useAuthContext';
import { useDashboard } from '../../api/hooks/useDashboard';
import { canUseAdminCapability, type AdminCapability } from '../../admin/permissions';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';

interface AdminNavItem {
  label: string;
  href: string;
  capability: AdminCapability;
  icon: ReactNode;
  companyOnly?: boolean;
}

const items: AdminNavItem[] = [
  { label: 'Overview', href: '/app/admin/overview', capability: 'overview', icon: <Gauge size={17} /> },
  { label: 'Company profile', href: '/app/admin/company', capability: 'company', icon: <Building2 size={17} />, companyOnly: true },
  { label: 'Employees', href: '/app/admin/employees', capability: 'employees', icon: <Users size={17} /> },
  { label: 'Managers', href: '/app/admin/managers', capability: 'managers', icon: <ShieldCheck size={17} /> },
  { label: 'Departments', href: '/app/admin/departments', capability: 'departments', icon: <Boxes size={17} /> },
  { label: 'Assets', href: '/app/admin/assets', capability: 'assets', icon: <HardDrive size={17} /> },
  { label: 'Software', href: '/app/admin/software', capability: 'software', icon: <PackageSearch size={17} /> },
  { label: 'Budgets', href: '/app/admin/budgets', capability: 'budgets', icon: <CircleDollarSign size={17} /> },
  { label: 'Suppliers', href: '/app/admin/suppliers', capability: 'suppliers', icon: <ClipboardCheck size={17} /> },
  { label: 'Holidays', href: '/app/admin/holidays', capability: 'holidays', icon: <CalendarDays size={17} /> },
  { label: 'Staffing rules', href: '/app/admin/staffing-rules', capability: 'staffing', icon: <Users size={17} /> },
  { label: 'Policy readiness', href: '/app/admin/policies', capability: 'policies', icon: <ShieldCheck size={17} /> },
  { label: 'Documents', href: '/app/admin/documents', capability: 'documents', icon: <FileText size={17} /> },
  { label: 'Operational issues', href: '/app/admin/failures', capability: 'failures', icon: <ShieldAlert size={17} />, companyOnly: true },
  { label: 'Capability gaps', href: '/app/admin/capability-gaps', capability: 'failures', icon: <ShieldAlert size={17} />, companyOnly: true },
];

export function AdminShell() {
  const { user } = useAuthContext();
  const dashboard = useDashboard();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const departmentType = dashboard.data?.identity.department_type;
  const companyName = dashboard.data?.identity.company_name ?? 'Company workspace';
  const visibleItems = useMemo(
    () => items.filter((item) => canUseAdminCapability(user, departmentType, item.capability)),
    [departmentType, user],
  );
  const current = visibleItems.find((item) => location.pathname.startsWith(item.href));
  const requested = items.find((item) => location.pathname.startsWith(item.href));
  const denied = Boolean(requested && !visibleItems.includes(requested));

  useEffect(() => setMobileOpen(false), [location.pathname]);

  return (
    <div className="min-h-full bg-neutral-50 dark:bg-neutral-950">
      <div className="border-b border-neutral-200 bg-indigo-950 text-white dark:border-neutral-800 dark:bg-indigo-950">
        <div className="flex min-h-16 items-center justify-between gap-4 px-4 sm:px-6">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">{companyName}</p>
            <p className="text-xs text-neutral-300">{departmentType ? `${departmentType.replaceAll('_', ' ')} administration` : 'Company administration'}</p>
          </div>
          <Button variant="secondary" size="sm" className="md:hidden" onClick={() => setMobileOpen(true)}>
            <Menu size={16} className="mr-2" />Sections
          </Button>
        </div>
      </div>

      <div className="flex min-h-[calc(100dvh-8rem)]">
        <aside className="hidden w-60 shrink-0 border-r border-neutral-200 bg-stone-900 p-3 dark:border-neutral-800 dark:bg-stone-900 md:block">
          <AdminNavigation items={visibleItems} />
        </aside>

        <section className="min-w-0 flex-1">
          <div className="border-b border-neutral-200 bg-indigo-950 px-4 py-2.5 dark:border-neutral-800 dark:bg-indigo-950 sm:px-6">
            <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-xs text-neutral-300">
              <span>Administration</span><ChevronRight size={13} aria-hidden="true" />
              <span className="font-medium text-white">{current?.label ?? 'Resource detail'}</span>
            </nav>
          </div>
          <main className="mx-auto max-w-[1500px] p-4 sm:p-6">{denied ? <AdminAccessDenied /> : <Outlet />}</main>
        </section>
      </div>

      <Modal title="Administration sections" isOpen={mobileOpen} onClose={() => setMobileOpen(false)}>
        <div className="flex items-center justify-between pb-2">
          <p className="text-xs text-neutral-500">Only sections authorized for your role are shown.</p>
          <button aria-label="Close administration sections" onClick={() => setMobileOpen(false)} className="sr-only"><X /></button>
        </div>
        <AdminNavigation items={visibleItems} />
      </Modal>
    </div>
  );
}

function AdminAccessDenied() {
  return <div className="mx-auto max-w-xl rounded-card border border-danger-200 bg-white p-8 text-center dark:border-danger-900 dark:bg-neutral-900"><ShieldAlert className="mx-auto text-danger-600" size={30} /><h1 className="mt-4 text-xl font-semibold">Administration access denied</h1><p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">This section is outside your department-management scope. Backend authorization remains authoritative.</p></div>;
}

function AdminNavigation({ items: navigation }: { items: AdminNavItem[] }) {
  return (
    <nav aria-label="Administration navigation" className="grid gap-1">
      {navigation.map((item) => (
        <NavLink
          key={item.href}
          to={item.href}
          className={({ isActive }) => clsx(
            'flex min-h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500',
            isActive
              ? 'bg-primary-700 text-white dark:bg-primary-700 dark:text-white'
              : 'text-neutral-300 hover:bg-white/5 hover:text-white dark:text-neutral-300 dark:hover:bg-white/5 dark:hover:text-white',
          )}
        >
          {item.icon}<span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
