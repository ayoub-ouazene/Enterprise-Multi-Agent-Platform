import { CircleHelp, MessageCircleQuestion, Radio } from 'lucide-react';
import type { DashboardResponse } from '../../api/types';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import {
  AttentionQueue, DashboardHeader, DashboardSection, QuickActions,
  RealtimeUpdateIndicator, RequestList,
} from '../components/DashboardPrimitives';

export function ExternalDashboard({ dashboard, isRefreshing }: { dashboard: DashboardResponse; isRefreshing: boolean }) {
  const navigate = useNavigate();
  return <PageContainer className="space-y-8">
    <DashboardHeader eyebrow={`${dashboard.identity.company_name} support`} title={`How can we help, ${dashboard.identity.account_label}?`} subtitle="Create a support request, answer clarification questions, and follow safe progress updates." action={<Button onClick={() => navigate('/app/requests/new')}>Create support request</Button>} status={<RealtimeUpdateIndicator refreshing={isRefreshing} />} />
    <DashboardSection title="Needs your attention"><AttentionQueue items={dashboard.attention} emptyMessage="No support request is waiting for your response." viewAll="/app/notifications" /></DashboardSection>
    <div className="grid gap-8 xl:grid-cols-[1.25fr_.75fr]">
      <DashboardSection title="Open support requests" description="Only requests created by your account are shown."><RequestList items={dashboard.active_requests} emptyTitle="You have no open support requests" /></DashboardSection>
      <DashboardSection title="How support works">
        <ol className="space-y-5"><HelpStep icon={<MessageCircleQuestion size={18} />} title="Describe the issue" text="Share the problem and the outcome you need." /><HelpStep icon={<CircleHelp size={18} />} title="Answer clarification" text="We may ask only for information needed to continue." /><HelpStep icon={<Radio size={18} />} title="Follow progress" text="Safe updates appear here and in notifications." /></ol>
      </DashboardSection>
    </div>
    <div className="grid gap-8 lg:grid-cols-2">
      <DashboardSection title="Recent results"><RequestList items={dashboard.completed_requests} emptyTitle="No completed support requests yet" emptyAction={false} /></DashboardSection>
      <DashboardSection title="Support shortcuts"><QuickActions items={[{ label: 'Create support request', description: 'Start a new issue or support process.', href: '/app/requests/new', primary: true }, { label: 'View all requests', description: 'Review your support history.', href: '/app/requests' }, { label: 'Open notifications', description: 'Read clarification and progress updates.', href: '/app/notifications' }]} /></DashboardSection>
    </div>
  </PageContainer>;
}

function HelpStep({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return <li className="flex gap-3"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-50 text-primary-600 dark:bg-primary-950">{icon}</span><div><p className="text-sm font-medium text-neutral-950 dark:text-white">{title}</p><p className="mt-1 text-xs leading-5 text-neutral-500">{text}</p></div></li>;
}
