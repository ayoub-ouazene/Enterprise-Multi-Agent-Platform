import { useParams } from 'react-router-dom';
import { useNavigate } from 'react-router-dom';
import {
  ClipboardList,
  Hand,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';
import { PageContainer, PageHeader, Section } from '../../../components/layout/PageContainer';
import { StatCard } from '../admin/components/StatCard';
import { StatusBadge } from '../admin/components/StatusBadge';
import { ErrorState } from '../admin/components/ErrorState';
import { useDepartmentStats, useDepartmentRequests, useDepartmentActions, useDepartmentReadiness } from '../../../api/hooks/useDepartments';
import { getDepartmentMeta, slugToDepartmentType } from '../../../lib/departments';
import { RequestStatus } from '../../../api/types';
import { relativeTime } from '../../../lib/formatters';

export function DepartmentOverviewPage() {
  const { deptSlug } = useParams<{ deptSlug: string }>();
  const navigate = useNavigate();
  const deptType = deptSlug ? slugToDepartmentType(deptSlug) : undefined;
  const meta = deptType ? getDepartmentMeta(deptType) : undefined;

  const {
    data: stats,
    error: statsError,
  } = useDepartmentStats(deptType ?? '');
  const { data: requests, isLoading: reqLoading } = useDepartmentRequests(deptType ?? '', { limit: 5 });
  const { data: actions, isLoading: actLoading } = useDepartmentActions(deptType ?? '', { limit: 5 });
  const { data: readiness } = useDepartmentReadiness(deptType ?? '');

  if (!deptType || !meta) {
    return (
      <PageContainer>
        <ErrorState message="The department does not exist." />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title={meta.label}
        description="Department workspace overview"
      />

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Active Requests"
          value={stats?.active_requests ?? 0}
          icon={<ClipboardList size={18} />}
          color="blue"
        />
        <StatCard
          label="Pending Actions"
          value={stats?.pending_human_actions ?? 0}
          icon={<Hand size={18} />}
          color={stats?.pending_human_actions ? 'amber' : 'emerald'}
        />
        <StatCard
          label="Collaborations"
          value={stats?.collaborations_ongoing ?? 0}
          icon={<RefreshCw size={18} />}
          color="purple"
        />
        <StatCard
          label="Completed Today"
          value={stats?.completed_today ?? 0}
          icon={<CheckCircle size={18} />}
          color="emerald"
        />
      </div>

      {statsError && (
        <div className="mt-4">
          <ErrorState message="Failed to load stats. Please try again." />
        </div>
      )}

      {/* Readiness */}
      {readiness && (
        <Section title="Readiness">
          <div className="space-y-2">
            {readiness.items.map((item) => (
              <div key={item.name} className="flex items-center justify-between rounded-md border border-neutral-200 bg-white px-4 py-2 dark:border-neutral-800 dark:bg-neutral-800">
                <span className="text-sm text-neutral-700 dark:text-neutral-300">{item.name}</span>
                <StatusBadge status={item.ready ? 'success' : 'warning'}>{item.ready ? 'Ready' : 'Not ready'}</StatusBadge>
              </div>
            ))}
          </div>
          {!readiness.overall_ready && (
            <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
              <AlertTriangle size={12} className="mr-1 inline" />
              Some readiness checks are failing. Review the items above.
            </p>
          )}
        </Section>
      )}

      {/* Recent requests */}
      <Section title="Recent Requests">
        <div className="mb-2 text-right">
          <button
            onClick={() => navigate(`/app/departments/${deptSlug}/requests`)}
            className="text-sm font-medium text-primary-600 hover:underline dark:text-primary-400"
          >
            View all
          </button>
        </div>
        {reqLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-12 animate-pulse rounded-md bg-neutral-100 dark:bg-neutral-800" />
            ))}
          </div>
        ) : !requests || requests.length === 0 ? (
          <p className="text-sm text-neutral-500 dark:text-neutral-400">No recent requests.</p>
        ) : (
          <div className="space-y-2">
            {requests.map((req) => (
              <button
                key={req.id}
                onClick={() => navigate(`/app/requests/${req.id}`)}
                className="flex w-full items-center justify-between rounded-md border border-neutral-200 bg-white px-4 py-2 text-left transition-colors hover:border-neutral-300 dark:border-neutral-800 dark:bg-neutral-800 dark:hover:border-neutral-700"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-100">{req.title}</p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400">{req.request_type} &middot; {relativeTime(req.created_at)}</p>
                </div>
                <StatusBadge
                  status={req.status === RequestStatus.COMPLETED ? 'success' : req.status === RequestStatus.FAILED ? 'error' : 'info'}
                >
                  {req.status.replace(/_/g, ' ')}
                </StatusBadge>
              </button>
            ))}
          </div>
        )}
      </Section>

      {/* Pending actions */}
      <Section title="Pending Actions">
        <div className="mb-2 text-right">
          <button
            onClick={() => navigate(`/app/departments/${deptSlug}/actions`)}
            className="text-sm font-medium text-primary-600 hover:underline dark:text-primary-400"
          >
            View all
          </button>
        </div>
        {actLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="h-12 animate-pulse rounded-md bg-neutral-100 dark:bg-neutral-800" />
            ))}
          </div>
        ) : !actions || actions.length === 0 ? (
          <p className="text-sm text-neutral-500 dark:text-neutral-400">No pending actions.</p>
        ) : (
          <div className="space-y-2">
            {actions.map((action) => (
              <button
                key={action.id}
                onClick={() => navigate(`/app/human-actions/${action.id}`)}
                className="flex w-full items-center justify-between rounded-md border border-neutral-200 bg-white px-4 py-2 text-left transition-colors hover:border-neutral-300 dark:border-neutral-800 dark:bg-neutral-800 dark:hover:border-neutral-700"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-100">{action.title}</p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400">{action.action_type}</p>
                </div>
                <StatusBadge status="warning">Pending</StatusBadge>
              </button>
            ))}
          </div>
        )}
      </Section>
    </PageContainer>
  );
}
