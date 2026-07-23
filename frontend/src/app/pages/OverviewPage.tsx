import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { useAuthContext } from '../../auth/hooks/useAuthContext';
import { isCompanyAccount, isDepartmentManager, isEmployee, isExternalUser } from '../../auth/permissions';
import { useRequests } from '../../api/hooks/useRequests';
import { useUnreadCount } from '../../api/hooks/useNotifications';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { EmptyState } from '../../components/ui/EmptyState';
import { RequestStatus } from '../../api/types';

export function OverviewPage() {
  const { user } = useAuthContext();
  const { data: requests, isLoading: requestsLoading } = useRequests({ limit: 5 });
  const { data: unreadData } = useUnreadCount();

  if (!user) return null;

  const activeRequests = requests?.filter(
    (r) => r.status !== RequestStatus.COMPLETED && r.status !== RequestStatus.CANCELLED && r.status !== RequestStatus.FAILED
  ) ?? [];

  const renderCompanyDashboard = () => (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Active Requests" value={activeRequests.length} variant="primary" />
        <StatCard title="Unread Notifications" value={unreadData?.unread_count ?? 0} variant="warning" />
        <StatCard title="Pending Actions" value={0} variant="danger" />
        <StatCard title="Employees" value={0} variant="success" />
      </div>

      <div className="mt-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Requests</CardTitle>
          </CardHeader>
          <CardContent>
            {requestsLoading ? <LoadingSpinner /> : activeRequests.length === 0 ? (
              <EmptyState title="No active requests" description="Recent requests will appear here." />
            ) : (
              <ul className="divide-y divide-gray-200">
                {activeRequests.map((req) => (
                  <li key={req.id} className="py-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{req.title}</p>
                        <p className="text-xs text-gray-500">{req.request_type}</p>
                      </div>
                      <StatusBadge status={req.status} />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );

  const renderManagerDashboard = () => (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard title="Department Requests" value={activeRequests.length} variant="primary" />
        <StatCard title="Pending Approvals" value={0} variant="warning" />
        <StatCard title="Unread Notifications" value={unreadData?.unread_count ?? 0} variant="info" />
      </div>
      <div className="mt-6">
        <Card>
          <CardHeader><CardTitle>Department Activity</CardTitle></CardHeader>
          <CardContent>
            <EmptyState title="No recent activity" description="Department requests will appear here." />
          </CardContent>
        </Card>
      </div>
    </>
  );

  const renderUserDashboard = () => (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <StatCard title="My Active Requests" value={activeRequests.length} variant="primary" />
        <StatCard title="Unread Notifications" value={unreadData?.unread_count ?? 0} variant="info" />
      </div>
      <div className="mt-6">
        <Card>
          <CardHeader><CardTitle>My Requests</CardTitle></CardHeader>
          <CardContent>
            {requestsLoading ? <LoadingSpinner /> : activeRequests.length === 0 ? (
              <EmptyState
                title="No active requests"
                description="Submit a new request to get started."
              />
            ) : (
              <ul className="divide-y divide-gray-200">
                {activeRequests.map((req) => (
                  <li key={req.id} className="py-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{req.title}</p>
                        <p className="text-xs text-gray-500">{req.status}</p>
                      </div>
                      <StatusBadge status={req.status} />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Overview</h1>
      {isCompanyAccount(user) && renderCompanyDashboard()}
      {isDepartmentManager(user) && renderManagerDashboard()}
      {(isEmployee(user) || isExternalUser(user)) && renderUserDashboard()}
    </div>
  );
}

function StatCard({ title, value }: { title: string; value: number; variant?: 'primary' | 'warning' | 'danger' | 'success' | 'info' }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-sm font-medium text-gray-600">{title}</p>
        <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
      </CardContent>
    </Card>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info'> = {
    draft: 'default',
    submitted: 'info',
    in_progress: 'primary',
    pending_approval: 'warning',
    pending_action: 'warning',
    completed: 'success',
    cancelled: 'default',
    failed: 'danger',
    rejected: 'danger',
  };
  return <Badge variant={variants[status] ?? 'default'}>{status.replace('_', ' ')}</Badge>;
}
