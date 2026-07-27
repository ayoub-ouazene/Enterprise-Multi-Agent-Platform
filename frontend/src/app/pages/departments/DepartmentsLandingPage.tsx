import {
  AlertTriangle,
  ArrowRight,
  Building2,
  CheckCircle,
  Clock,
  Headphones,
  Landmark,
  Monitor,
  Settings,
  ShoppingCart,
  Users,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useDepartments, useDepartmentReadiness, useDepartmentStats } from '../../../api/hooks/useDepartments';
import { useDashboard } from '../../../api/hooks/useDashboard';
import { useAuthContext } from '../../../auth/hooks/useAuthContext';
import { ActorType } from '../../../api/types';
import { DEPARTMENT_REGISTRY, getDepartmentMeta } from '../../../lib/departments';
import { PageContainer, PageHeader } from '../../../components/layout/PageContainer';
import { Alert } from '../../../components/ui/Alert';
import { Button } from '../../../components/ui/Button';
import { StatusBadge } from '../admin/components/StatusBadge';
import { TableSkeleton } from '../admin/components/TableSkeleton';

const icons = { Headphones, Users, Monitor, Landmark, ShoppingCart };

export function DepartmentsLandingPage() {
  const { user } = useAuthContext();
  const departments = useDepartments();
  const dashboard = useDashboard();

  if (departments.isLoading) return <PageContainer><TableSkeleton rows={5} /></PageContainer>;
  if (departments.isError) {
    return <PageContainer><Alert variant="error">Department workspaces are unavailable or outside your access scope.</Alert></PageContainer>;
  }

  const managerMap = new Map(
    (dashboard.data?.departments ?? []).map((d) => [d.department_type, d])
  );

  return (
    <PageContainer>
      <PageHeader
        title="Department workspaces"
        description={user?.actor_type === ActorType.COMPANY
          ? 'Operational workload, readiness, and action queues across the five fixed departments.'
          : 'Your authorized department workload and operational resources.'}
      />
      <div className="grid gap-4 lg:grid-cols-2">
        {departments.data?.map((department) => (
          <DepartmentLandingCard key={department.id} department={department} dashboardInfo={managerMap.get(department.department_type)} />
        ))}
      </div>
      {departments.data?.length === 0 && (
        <Alert variant="warning" title="No accessible department">
          Your account is not assigned to an active department workspace. Contact the Company account.
        </Alert>
      )}
    </PageContainer>
  );
}

function DepartmentLandingCard({
  department,
  dashboardInfo,
}: {
  department: { id: string; name: string; department_type: string; is_active: boolean };
  dashboardInfo?: { manager_label: string | null; ready: boolean; active_requests: number; pending_actions: number } | null;
}) {
  const navigate = useNavigate();
  const meta = getDepartmentMeta(department.department_type);
  const stats = useDepartmentStats(department.department_type);
  const readiness = useDepartmentReadiness(department.department_type);
  if (!meta) return null;
  const Icon = icons[meta.icon];
  const warningCount = readiness.data?.items.filter((item) => !item.ready).length ?? 0;
  const isReady = department.is_active && (dashboardInfo?.ready ?? readiness.data?.overall_ready ?? true);

  return (
    <article className="rounded-card border border-neutral-200 bg-white p-5 shadow-card transition-colors hover:border-primary-300 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 gap-3">
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl" style={{ backgroundColor: meta.lightColor, color: meta.darkColor }}>
            <Icon size={20} aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <h2 className="font-semibold text-neutral-950 dark:text-white">{meta.label}</h2>
            <p className="mt-1 text-sm leading-5 text-neutral-500">{meta.description}</p>
            {dashboardInfo?.manager_label && (
              <p className="mt-1 truncate text-xs text-neutral-400">
                <Users size={11} className="mr-1 inline" />Manager: {dashboardInfo.manager_label}
              </p>
            )}
            {warningCount > 0 && (
              <p className="mt-1 flex items-center gap-1 text-xs text-warning-600 dark:text-warning-300">
                <AlertTriangle size={11} /> {warningCount} setup item{warningCount !== 1 ? 's' : ''} need attention
              </p>
            )}
          </div>
        </div>
        <StatusBadge status={!department.is_active ? 'neutral' : isReady ? 'success' : 'warning'}>
          {!department.is_active ? 'Disabled' : isReady ? 'Ready' : 'Setup needed'}
        </StatusBadge>
      </div>
      <dl className="mt-5 grid grid-cols-4 gap-2 rounded-xl bg-neutral-50 p-3 dark:bg-neutral-800/70">
        <Metric label="Active" value={dashboardInfo?.active_requests ?? stats.data?.active_requests ?? '—'} icon={<Building2 size={13} />} />
        <Metric label="Actions" value={dashboardInfo?.pending_actions ?? stats.data?.pending_human_actions ?? '—'} icon={<Clock size={13} />} />
        <Metric label="Completed" value={stats.data?.completed_today ?? '—'} icon={<CheckCircle size={13} />} />
        <Metric label="Warnings" value={warningCount} icon={<Settings size={13} />} />
      </dl>
      {!department.is_active && (
        <p className="mt-3 flex items-center gap-2 text-sm text-warning-700 dark:text-warning-300">
          <AlertTriangle size={15} /> Enable this department from Company Administration.
        </p>
      )}
      <Button
        className="mt-4 w-full"
        variant={department.is_active ? 'primary' : 'secondary'}
        disabled={!department.is_active}
        onClick={() => navigate(`/app/departments/${meta.slug}/overview`)}
      >
        Open workspace <ArrowRight size={15} className="ml-2" />
      </Button>
    </article>
  );
}

function Metric({ label, value, icon }: { label: string; value: number | string; icon?: React.ReactNode }) {
  return (
    <div>
      <dt className="flex items-center gap-1 text-[11px] font-medium text-neutral-500">
        {icon}{label}
      </dt>
      <dd className="mt-1 text-lg font-semibold">{value}</dd>
    </div>
  );
}

export const departmentRegistryCount = Object.keys(DEPARTMENT_REGISTRY).length;
