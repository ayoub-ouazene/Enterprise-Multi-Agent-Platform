import type { DashboardResponse } from '../../api/types';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import {
  AttentionQueue, DashboardHeader, DashboardMetricGrid, DashboardSection,
  PendingActions, QuickActions, RealtimeUpdateIndicator, RequestList,
} from '../components/DashboardPrimitives';

export function EmployeeDashboard({ dashboard, isRefreshing }: { dashboard: DashboardResponse; isRefreshing: boolean }) {
  const navigate = useNavigate();
  return <PageContainer className="space-y-8">
    <DashboardHeader eyebrow={dashboard.identity.department_name ?? 'Employee workspace'} title={`Welcome back, ${dashboard.identity.account_label}`} subtitle="Track your requests, provide required information, and review recent results." action={<Button onClick={() => navigate('/app/requests/new')}>Create request</Button>} status={<RealtimeUpdateIndicator refreshing={isRefreshing} />} />
    <DashboardSection title="Your attention" description="Items that need your response come first."><AttentionQueue items={dashboard.attention} emptyMessage="You have no requests waiting for your input." /></DashboardSection>
    <DashboardMetricGrid metrics={dashboard.metrics} />
    <div className="grid gap-8 xl:grid-cols-[1.3fr_.7fr]">
      <DashboardSection title="Active requests" description="Your current work, bounded to the latest updates."><RequestList items={dashboard.active_requests} emptyTitle="You have no active requests" /></DashboardSection>
      <DashboardSection title="Pending actions" description="Only actions assigned to your account."><PendingActions items={dashboard.pending_actions} /></DashboardSection>
    </div>
    <div className="grid gap-8 lg:grid-cols-2">
      <DashboardSection title="Recently completed"><RequestList items={dashboard.completed_requests} emptyTitle="No completed requests yet" emptyAction={false} /></DashboardSection>
      <DashboardSection title="Quick actions"><QuickActions items={[{ label: 'Create request', description: 'Ask for help or start a permitted process.', href: '/app/requests/new', primary: true }, { label: 'View all requests', description: 'Review your complete request list.', href: '/app/requests' }, { label: 'Pending actions', description: 'Provide requested information.', href: '/app/human-actions' }, { label: 'Notifications', description: 'Read request and system updates.', href: '/app/notifications' }]} /></DashboardSection>
    </div>
  </PageContainer>;
}
