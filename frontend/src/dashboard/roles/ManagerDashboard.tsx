import { BriefcaseBusiness } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import type { DashboardResponse } from '../../api/types';
import { PageContainer } from '../../components/layout/PageContainer';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import {
  ActivityFeed, AttentionQueue, DashboardHeader, DashboardMetricGrid,
  DashboardSection, PendingActions, QuickActions, RealtimeUpdateIndicator,
  RequestList,
} from '../components/DashboardPrimitives';

const operationalLabels: Record<string, string> = {
  customer_support: 'Support operations', hr: 'People operations', it: 'Technology operations',
  finance: 'Financial controls', procurement: 'Procurement operations',
};

export function ManagerDashboard({ dashboard, isRefreshing }: { dashboard: DashboardResponse; isRefreshing: boolean }) {
  const navigate = useNavigate();
  const type = dashboard.identity.department_type ?? '';
  const workspace = `/app/departments/${type}/overview`;
  return <PageContainer className="space-y-8">
    <DashboardHeader eyebrow="Department manager" title={`${dashboard.identity.department_name ?? 'Department'} workspace`} subtitle={`Prioritized workload and ${operationalLabels[type] ?? 'department operations'} for your approved scope only.`} action={<Button onClick={() => navigate('/app/human-actions')}>Review pending actions</Button>} status={<div className="flex flex-wrap gap-2"><Badge variant={dashboard.readiness.every((item) => item.ready) ? 'success' : 'warning'}>{dashboard.readiness.every((item) => item.ready) ? 'Department ready' : 'Readiness issue'}</Badge><RealtimeUpdateIndicator refreshing={isRefreshing} /></div>} />
    <DashboardSection title="Attention required" description="Department-scoped actions and blockers."><AttentionQueue items={dashboard.attention} emptyMessage="Your department has no pending urgent work." /></DashboardSection>
    <DashboardSection title="Workload summary"><DashboardMetricGrid metrics={dashboard.metrics} /></DashboardSection>
    <div className="grid gap-8 xl:grid-cols-[1.3fr_.7fr]">
      <DashboardSection title="Active department work" description="Owned requests and active collaborations."><RequestList items={dashboard.active_requests} emptyTitle="Your department has no active requests" /></DashboardSection>
      <DashboardSection title="Assigned actions" description="Approvals and tasks that can move work forward."><PendingActions items={dashboard.pending_actions} /></DashboardSection>
    </div>
    <div className="grid gap-8 lg:grid-cols-2">
      <DashboardSection title={operationalLabels[type] ?? 'Operational readiness'} description="Concise readiness checks for this department."><div className="space-y-3">{dashboard.readiness.map((item) => <div key={item.key} className="flex items-center justify-between rounded-xl border border-neutral-200 bg-white px-4 py-3 dark:border-neutral-800 dark:bg-neutral-900"><div className="flex items-center gap-3"><BriefcaseBusiness size={17} className="text-neutral-400" /><div><p className="text-sm font-medium">{item.label}</p><p className="text-xs text-neutral-500">{item.detail}</p></div></div><Badge variant={item.ready ? 'success' : 'warning'}>{item.ready ? 'Ready' : 'Needs setup'}</Badge></div>)}</div><Link to={workspace} className="mt-4 inline-block text-sm font-semibold text-primary-600">Open department workspace</Link></DashboardSection>
      <DashboardSection title="Recent department activity"><ActivityFeed items={dashboard.activity} /></DashboardSection>
    </div>
    <DashboardSection title="Manager shortcuts"><QuickActions items={[{ label: 'Create a request', description: 'Start new department work.', href: '/app/requests/new', primary: true }, { label: 'Department requests', description: 'Review all visible department requests.', href: `/app/departments/${type}/requests` }, { label: 'Department workspace', description: 'Open operational resources and settings.', href: workspace }, { label: 'Notifications', description: 'Review recent updates.', href: '/app/notifications' }]} /></DashboardSection>
  </PageContainer>;
}
