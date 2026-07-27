import { Building2, CheckCircle2, Circle } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import type { DashboardResponse } from '../../api/types';
import { PageContainer } from '../../components/layout/PageContainer';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import {
  ActivityFeed, AttentionQueue, DashboardHeader, DashboardMetricGrid,
  DashboardSection, QuickActions, RealtimeUpdateIndicator,
} from '../components/DashboardPrimitives';

export function CompanyDashboard({ dashboard, isRefreshing }: { dashboard: DashboardResponse; isRefreshing: boolean }) {
  const navigate = useNavigate();
  const ready = dashboard.readiness.filter((item) => item.ready).length;
  return <PageContainer className="space-y-8">
    <DashboardHeader eyebrow="Company account" title={`${dashboard.identity.company_name} overview`} subtitle="Company readiness, work requiring attention, and operational activity across your workspace." action={<Button onClick={() => navigate('/app/requests/new')}>Create request</Button>} status={<div className="flex flex-wrap items-center gap-2"><Badge variant={dashboard.identity.company_active ? 'success' : 'warning'}>{dashboard.identity.company_active ? 'Company active' : 'Activation pending'}</Badge><Badge variant={ready === dashboard.readiness.length ? 'success' : 'warning'}>{ready}/{dashboard.readiness.length} readiness checks</Badge><RealtimeUpdateIndicator refreshing={isRefreshing} /></div>} />

    <DashboardSection title="Attention required" description="Resolve blockers before reviewing general activity.">
      <AttentionQueue items={dashboard.attention} emptyMessage="Company setup and active work have no immediate blockers." />
    </DashboardSection>

    <DashboardSection title="Operational state" description="Authoritative company-scoped totals.">
      <DashboardMetricGrid metrics={dashboard.metrics} />
    </DashboardSection>

    <div className="grid gap-8 xl:grid-cols-[1.35fr_.65fr]">
      <DashboardSection title="Department overview" description="Enabled teams, manager coverage, and current workload.">
        <div className="grid gap-3 sm:grid-cols-2">
          {dashboard.departments.map((department) => <Link key={department.id} to={`/app/departments/${department.department_type}/overview`} className="rounded-card border border-neutral-200 bg-white p-4 shadow-xs hover:border-primary-300 dark:border-neutral-800 dark:bg-neutral-900"><div className="flex items-start justify-between gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"><Building2 size={17} /></span><Badge variant={department.ready ? 'success' : 'warning'}>{department.ready ? 'Ready' : 'Setup needed'}</Badge></div><p className="mt-4 font-semibold text-neutral-950 dark:text-white">{department.name}</p><p className="mt-1 truncate text-xs text-neutral-500">{department.manager_label ?? 'No manager assigned'}</p><div className="mt-4 flex gap-4 text-xs text-neutral-500"><span><strong className="text-neutral-900 dark:text-white">{department.active_requests}</strong> active</span><span><strong className="text-neutral-900 dark:text-white">{department.pending_actions}</strong> actions</span></div></Link>)}
        </div>
      </DashboardSection>

      <DashboardSection title="Company readiness" description="Explicit fixed onboarding checks." action={<Link to="/app/onboarding" className="text-sm font-semibold text-primary-600">Review setup</Link>}>
        <ul className="space-y-3">{dashboard.readiness.map((item) => <li key={item.key} className="flex gap-3">{item.ready ? <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-success-600" /> : <Circle size={18} className="mt-0.5 shrink-0 text-warning-600" />}<div><p className="text-sm font-medium text-neutral-900 dark:text-white">{item.label}</p>{item.detail && <p className="mt-0.5 text-xs text-neutral-500">{item.detail}</p>}</div></li>)}</ul>
      </DashboardSection>
    </div>

    <div className="grid gap-8 lg:grid-cols-2">
      <DashboardSection title="Recent activity" description="Safe updates delivered to this Company account."><ActivityFeed items={dashboard.activity} /></DashboardSection>
      <DashboardSection title="Quick actions" description="Common Company administration paths."><QuickActions items={[{ label: 'Review pending actions', description: 'Open approvals and operational confirmations.', href: '/app/human-actions', primary: true }, { label: 'Manage employees', description: 'Review the employee directory and responsibilities.', href: '/app/admin/employees' }, { label: 'Assign managers', description: 'Complete department leadership coverage.', href: '/app/admin/managers' }, { label: 'Manage policies', description: 'Review company knowledge and policy coverage.', href: '/app/admin/documents' }]} /></DashboardSection>
    </div>
  </PageContainer>;
}
