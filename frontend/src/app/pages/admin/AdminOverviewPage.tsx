import { Users, Layers, ClipboardList, Hand, ShieldCheck, AlertCircle } from 'lucide-react';
import { useAdminSummary } from '../../../api/hooks/useAdmin';
import { StatCard } from './components/StatCard';
import { SectionCard } from './components/SectionCard';
import { StatusBadge } from './components/StatusBadge';

export function AdminOverviewPage() {
  const { data: summary, isLoading, error } = useAdminSummary();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-28 animate-pulse rounded-xl bg-neutral-200 dark:bg-neutral-800" />
        ))}
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="rounded-lg border border-error-200 bg-error-50 p-4 text-sm text-error-700 dark:border-error-800 dark:bg-error-900/20 dark:text-error-300">
        <div className="flex items-center gap-2">
          <AlertCircle size={16} />
          Failed to load admin summary.
        </div>
      </div>
    );
  }

  const cards = [
    { label: 'Total Employees', value: summary.total_employees, icon: <Users size={18} />, color: 'blue' as const },
    { label: 'Departments', value: summary.total_departments, icon: <Layers size={18} />, color: 'purple' as const },
    { label: 'Active Requests', value: summary.active_requests, icon: <ClipboardList size={18} />, color: 'amber' as const },
    { label: 'Pending Actions', value: summary.pending_human_actions, icon: <Hand size={18} />, color: 'rose' as const },
    { label: 'Policy Ready', value: summary.policy_ready ? 'Yes' : 'No', icon: <ShieldCheck size={18} />, color: summary.policy_ready ? 'emerald' as const : 'amber' as const },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((card) => (
          <StatCard key={card.label} {...card} />
        ))}
      </div>

      <SectionCard title="Quick Navigation" description="Jump to an administration area">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {quickLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={(e) => {
                e.preventDefault();
                window.history.pushState(null, '', link.href);
                window.dispatchEvent(new PopStateEvent('popstate'));
              }}
              className="flex items-center gap-3 rounded-lg border border-neutral-200 bg-white p-3 text-sm font-medium text-neutral-700 transition-colors hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700 dark:border-neutral-800 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:border-primary-700 dark:hover:bg-primary-900/20"
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary-100 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400">
                {link.icon}
              </span>
              {link.label}
            </a>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Status Overview">
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-neutral-600 dark:text-neutral-400">Policy Coverage</span>
            <StatusBadge status={summary.policy_ready ? 'success' : 'warning'}>
              {summary.policy_ready ? 'Ready' : 'Incomplete'}
            </StatusBadge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-neutral-600 dark:text-neutral-400">Active Workflows</span>
            <span className="font-medium text-neutral-900 dark:text-neutral-100">{summary.active_requests}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-neutral-600 dark:text-neutral-400">Human Actions Pending</span>
            <span className="font-medium text-neutral-900 dark:text-neutral-100">{summary.pending_human_actions}</span>
          </div>
        </div>
      </SectionCard>
    </div>
  );
}

const quickLinks = [
  { label: 'Employee Directory', href: '/app/admin/employees', icon: <Users size={16} /> },
  { label: 'Departments', href: '/app/admin/departments', icon: <Layers size={16} /> },
  { label: 'Company Profile', href: '/app/admin/company', icon: <ClipboardList size={16} /> },
  { label: 'Asset Inventory', href: '/app/admin/assets', icon: <ClipboardList size={16} /> },
  { label: 'Budgets', href: '/app/admin/budgets', icon: <ClipboardList size={16} /> },
  { label: 'Policies', href: '/app/admin/policies', icon: <ClipboardList size={16} /> },
];
