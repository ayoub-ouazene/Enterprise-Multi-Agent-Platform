import { ActorType } from '../api/types';
import { useDashboard } from '../api/hooks/useDashboard';
import { useAuthContext } from '../auth/hooks/useAuthContext';
import { DashboardErrorBoundary, DashboardSkeleton, FullDashboardError } from './components/DashboardPrimitives';
import { CompanyDashboard } from './roles/CompanyDashboard';
import { ManagerDashboard } from './roles/ManagerDashboard';
import { EmployeeDashboard } from './roles/EmployeeDashboard';
import { ExternalDashboard } from './roles/ExternalDashboard';

export function DashboardPage() {
  const { user } = useAuthContext();
  const query = useDashboard();

  if (!user) return null;
  if (query.isLoading) return <DashboardSkeleton />;
  if (query.isError || !query.data) return <FullDashboardError onRetry={() => query.refetch()} />;

  const dashboard = query.data;
  return (
    <DashboardErrorBoundary>
      {user.actor_type === ActorType.COMPANY && <CompanyDashboard dashboard={dashboard} isRefreshing={query.isFetching} />}
      {user.actor_type === ActorType.DEPARTMENT_MANAGER && <ManagerDashboard dashboard={dashboard} isRefreshing={query.isFetching} />}
      {user.actor_type === ActorType.EMPLOYEE && <EmployeeDashboard dashboard={dashboard} isRefreshing={query.isFetching} />}
      {user.actor_type === ActorType.EXTERNAL_USER && <ExternalDashboard dashboard={dashboard} isRefreshing={query.isFetching} />}
    </DashboardErrorBoundary>
  );
}
