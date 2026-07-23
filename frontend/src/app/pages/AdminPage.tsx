import { Building2, ShieldCheck, Users, Wallet, Wrench, Truck, FileText, BarChart3 } from 'lucide-react';
import { PageContainer, PageHeader, Section } from '../../components/layout/PageContainer';
import { useAuthContext } from '../../auth/hooks/useAuthContext';
import { isCompanyAccount } from '../../auth/permissions';

const adminAreas = [
  { label: 'Employee Directory', icon: <Users size={16} />, description: 'Manage employees and roles.' },
  { label: 'Department Structure', icon: <Building2 size={16} />, description: 'Configure departments and managers.' },
  { label: 'Asset Inventory', icon: <Wrench size={16} />, description: 'Track company assets and assignments.' },
  { label: 'Software Catalog', icon: <FileText size={16} />, description: 'Manage software and licenses.' },
  { label: 'Budget & Plans', icon: <Wallet size={16} />, description: 'Financial planning and budgets.' },
  { label: 'Suppliers & Procurement', icon: <Truck size={16} />, description: 'Vendor and supplier management.' },
  { label: 'Policy & Readiness', icon: <ShieldCheck size={16} />, description: 'Company policies and compliance.' },
  { label: 'Analytics', icon: <BarChart3 size={16} />, description: 'Reports and activity metrics.' },
];

export function AdminPage() {
  const { user } = useAuthContext();

  return (
    <PageContainer>
      <PageHeader title="Administration" description="Manage company resources and settings" />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {adminAreas.map((area) => (
          <button
            key={area.label}
            className="flex items-start gap-4 rounded-lg border border-neutral-200 bg-white p-4 text-left transition-colors hover:border-neutral-300 hover:shadow-sm dark:border-neutral-800 dark:bg-neutral-800 dark:hover:border-neutral-700"
            disabled
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-300">
              {area.icon}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{area.label}</h3>
              <p className="mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">{area.description}</p>
            </div>
          </button>
        ))}
      </div>

      {user && (
        <Section title="Current User" className="mt-6">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Email</p>
              <p className="mt-1 text-sm font-medium text-neutral-900 dark:text-neutral-100">{user.email}</p>
            </div>
            <div>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Role</p>
              <p className="mt-1 text-sm font-medium text-neutral-900 dark:text-neutral-100 capitalize">{user.actor_type.replace(/_/g, ' ')}</p>
            </div>
            <div>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Permissions</p>
              <p className="mt-1 text-sm text-neutral-700 dark:text-neutral-300">{user.permissions.join(', ') || 'None'}</p>
            </div>
            <div>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Department Access</p>
              <p className="mt-1 text-sm font-medium text-neutral-900 dark:text-neutral-100">
                {isCompanyAccount(user) ? 'All departments' : user.department_id ? 'Assigned department' : 'None'}
              </p>
            </div>
          </div>
        </Section>
      )}
    </PageContainer>
  );
}
