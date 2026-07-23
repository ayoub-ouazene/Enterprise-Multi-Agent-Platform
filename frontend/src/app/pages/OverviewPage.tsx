import { Activity, AlertTriangle, Bell, CheckCircle, Clock, FileWarning, Users } from 'lucide-react';
import { PageContainer, PageHeader, Section } from '../../components/layout/PageContainer';
import { MetricCard, StatusDot } from '../../components/layout/MetricCard';
import { MetricCardSkeleton } from '../../components/layout/Skeleton';
import { RequestSummaryCard } from '../../components/request/RequestSummaryCard';
import { EmptyState } from '../../components/ui/EmptyState';
import { useAuthContext } from '../../auth/hooks/useAuthContext';
import {
  isCompanyAccount,
  isDepartmentManager,
  isEmployee,
  isExternalUser,
} from '../../auth/permissions';
import { useRequests } from '../../api/hooks/useRequests';
import { useUnreadCount } from '../../api/hooks/useNotifications';
import { useHumanActions } from '../../api/hooks/useHumanActions';
import { useOnboardingStatus } from '../../api/hooks/useOnboarding';
import { RequestStatus } from '../../api/types';
import { getHumanActionStatusMeta } from '../../lib/status';
import { relativeTime } from '../../lib/formatters';
import { useNavigate } from 'react-router-dom';

export function OverviewPage() {
  const { user } = useAuthContext();
  if (!user) return null;

  return (
    <PageContainer>
      <PageHeader
        title={isCompanyAccount(user) ? 'Company Dashboard' : isDepartmentManager(user) ? 'Department Dashboard' : 'My Dashboard'}
        description={isCompanyAccount(user) ? 'Overview of your company operations' : isDepartmentManager(user) ? 'Department activity and requests' : 'Your personal request summary'}
      />
      {isCompanyAccount(user) && <CompanyDashboard />}
      {isDepartmentManager(user) && <ManagerDashboard />}
      {(isEmployee(user) || isExternalUser(user)) && <UserDashboard />}
    </PageContainer>
  );
}

/* ================= Company Dashboard ================= */
function CompanyDashboard() {
  const navigate = useNavigate();
  const { data: requests, isLoading: rLoading } = useRequests({ limit: 20 });
  const { data: unreadData } = useUnreadCount();
  const { data: actions, isLoading: aLoading } = useHumanActions({ limit: 10 });
  const { data: onboarding, isLoading: oLoading } = useOnboardingStatus();

  const activeRequests = requests?.filter(
    (r) => r.status !== RequestStatus.COMPLETED && r.status !== RequestStatus.CANCELLED && r.status !== RequestStatus.FAILED
  ) ?? [];
  const failedRequests = requests?.filter((r) => r.status === RequestStatus.FAILED || r.status === RequestStatus.REJECTED) ?? [];
  const overdueActions = actions?.filter((a) => a.due_date && new Date(a.due_date) < new Date()) ?? [];

  const metrics = (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        title="Attention Required"
        value={overdueActions.length + (unreadData?.unread_count ?? 0)}
        subtitle={`${overdueActions.length} overdue actions`}
        icon={<AlertTriangle size={20} />}
        category="attention"
        onClick={() => navigate('/app/human-actions')}
      />
      <MetricCard
        title="Active Requests"
        value={activeRequests.length}
        subtitle={`${failedRequests.length} failed`}
        icon={<Clock size={20} />}
        category="inProgress"
        onClick={() => navigate('/app/requests')}
      />
      <MetricCard
        title="Onboarding"
        value={onboarding?.onboarding_complete ? 'Complete' : 'Pending'}
        subtitle={onboarding?.missing_steps.length ? `${onboarding.missing_steps.length} steps missing` : undefined}
        icon={<CheckCircle size={20} />}
        category={onboarding?.onboarding_complete ? 'success' : 'pending'}
        onClick={() => navigate('/app/onboarding')}
      />
      <MetricCard
        title="Notifications"
        value={unreadData?.unread_count ?? 0}
        subtitle="Unread"
        icon={<Bell size={20} />}
        category="info"
        onClick={() => navigate('/app/notifications')}
      />
    </div>
  );

  return (
    <div className="space-y-6">
      {rLoading || aLoading || oLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCardSkeleton /><MetricCardSkeleton /><MetricCardSkeleton /><MetricCardSkeleton />
        </div>
      ) : metrics}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Section title="Recent Requests">
          <RecentRequests requests={activeRequests.slice(0, 5)} />
        </Section>
        <Section title="Recent Activity">
          <ActivityFeed />
        </Section>
      </div>
    </div>
  );
}

/* ================= Manager Dashboard ================= */
function ManagerDashboard() {
  const navigate = useNavigate();
  const { data: requests, isLoading: rLoading } = useRequests({ limit: 20 });
  const { data: unreadData } = useUnreadCount();
  const { data: actions } = useHumanActions({ limit: 10 });

  const activeRequests = requests?.filter(
    (r) => r.status !== RequestStatus.COMPLETED && r.status !== RequestStatus.CANCELLED && r.status !== RequestStatus.FAILED
  ) ?? [];
  const overdueActions = actions?.filter((a) => a.due_date && new Date(a.due_date) < new Date()) ?? [];

  return (
    <div className="space-y-6">
      {rLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <MetricCardSkeleton /><MetricCardSkeleton /><MetricCardSkeleton />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <MetricCard title="Department Requests" value={activeRequests.length} subtitle="Active" icon={<FileWarning size={20} />} category="inProgress" onClick={() => navigate('/app/requests')} />
          <MetricCard title="Pending Approvals" value={overdueActions.length} subtitle={overdueActions.length > 0 ? 'Overdue' : 'Up to date'} icon={<Users size={20} />} category={overdueActions.length > 0 ? 'attention' : 'success'} onClick={() => navigate('/app/human-actions')} />
          <MetricCard title="Notifications" value={unreadData?.unread_count ?? 0} subtitle="Unread" icon={<Bell size={20} />} category="info" onClick={() => navigate('/app/notifications')} />
        </div>
      )}
      <Section title="Recent Requests">
        <RecentRequests requests={activeRequests.slice(0, 5)} />
      </Section>
    </div>
  );
}

/* ================= Employee / External Dashboard ================= */
function UserDashboard() {
  const navigate = useNavigate();
  const { data: requests, isLoading } = useRequests({ limit: 10 });
  const { data: unreadData } = useUnreadCount();

  const activeRequests = requests?.filter(
    (r) => r.status !== RequestStatus.COMPLETED && r.status !== RequestStatus.CANCELLED && r.status !== RequestStatus.FAILED
  ) ?? [];
  const completedRequests = requests?.filter((r) => r.status === RequestStatus.COMPLETED) ?? [];

  return (
    <div className="space-y-6">
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <MetricCardSkeleton /><MetricCardSkeleton />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <MetricCard title="My Active Requests" value={activeRequests.length} subtitle={`${completedRequests.length} completed`} icon={<Activity size={20} />} category="inProgress" onClick={() => navigate('/app/requests')} />
          <MetricCard title="Notifications" value={unreadData?.unread_count ?? 0} subtitle="Unread" icon={<Bell size={20} />} category="info" onClick={() => navigate('/app/notifications')} />
        </div>
      )}
      <Section title="My Requests">
        <RecentRequests requests={(requests ?? []).slice(0, 5)} />
      </Section>
    </div>
  );
}

/* ================= Shared ================= */
function RecentRequests({ requests }: { requests: Array<{ id: string; title: string; request_type: string; summary: string; status: string; current_stage: string; priority: string }> }) {
  const navigate = useNavigate();

  if (requests.length === 0) {
    return <EmptyState title="No requests" description="Requests will appear here when submitted." action={<button onClick={() => navigate('/app/requests/new')} className="text-sm font-medium text-primary-600 hover:underline dark:text-primary-400">Submit a request</button>} />;
  }

  return (
    <div className="space-y-3">
      {requests.map((req) => (
        <RequestSummaryCard
          key={req.id}
          request={req as any}
          onClick={() => navigate(`/app/requests/${req.id}`)}
        />
      ))}
    </div>
  );
}

function ActivityFeed() {
  const { data: actions, isLoading } = useHumanActions({ limit: 5 });

  if (isLoading) return <div className="space-y-4"><MetricCardSkeleton /></div>;
  if (!actions || actions.length === 0) return <EmptyState title="No recent activity" description="Actions and updates will appear here." />;

  return (
    <div className="space-y-4">
      {actions.map((action) => {
        const meta = getHumanActionStatusMeta(action.status);
        return (
          <div key={action.id} className="flex items-start gap-3">
            <StatusDot category={meta.category} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                {action.title}
              </p>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                {action.action_type} • {relativeTime(action.created_at)}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
