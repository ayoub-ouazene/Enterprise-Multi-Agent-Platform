import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { EmptyState } from '../../components/ui/EmptyState';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { useRequests } from '../../api/hooks/useRequests';

export function RequestsPage() {
  const navigate = useNavigate();
  const { data: requests, isLoading, error, refetch } = useRequests({ limit: 50 });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <EmptyState title="Error loading requests" action={<Button onClick={() => refetch()}>Retry</Button>} />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Requests</h1>
        <Button onClick={() => navigate('/app/requests/new')}>New Request</Button>
      </div>

      {requests && requests.length > 0 ? (
        <div className="space-y-3">
          {requests.map((req) => (
            <Card
              key={req.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => navigate(`/app/requests/${req.id}`)}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900">{req.title}</h3>
                    <p className="mt-1 text-sm text-gray-500">{req.request_type}</p>
                    <p className="mt-1 text-sm text-gray-600 line-clamp-2">{req.summary}</p>
                  </div>
                  <StatusBadge status={req.status} />
                </div>
                <div className="mt-3 flex items-center gap-2 text-xs text-gray-500">
                  <span>Stage: {req.current_stage}</span>
                  <span>Priority: {req.priority}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12">
            <EmptyState
              title="No requests yet"
              description="Create your first request to get started."
              action={<Button onClick={() => navigate('/app/requests/new')}>New Request</Button>}
            />
          </CardContent>
        </Card>
      )}
    </div>
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
