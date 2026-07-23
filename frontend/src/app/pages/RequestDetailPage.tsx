import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Alert } from '../../components/ui/Alert';
import { EmptyState } from '../../components/ui/EmptyState';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { useRequest, useCancelRequest } from '../../api/hooks/useRequests';

export function RequestDetailPage() {
  const { requestId = '' } = useParams();
  const navigate = useNavigate();
  const { data: request, isLoading, error } = useRequest(requestId);
  const cancelMutation = useCancelRequest();

  if (isLoading) return <LoadingSpinner />;
  if (error || !request) {
    return (
      <EmptyState
        title="Request not found"
        description="The request you are looking for does not exist."
        action={<Button onClick={() => navigate('/app/requests')}>Back to requests</Button>}
      />
    );
  }

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel this request?')) return;
    try {
      await cancelMutation.mutateAsync(requestId);
    } catch {
      // ignore
    }
  };

  const canCancel = ['draft', 'submitted', 'in_progress'].includes(request.status);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => navigate('/app/requests')}>
          <svg className="mr-1 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
          Back
        </Button>
        {canCancel && (
          <Button variant="danger" onClick={handleCancel} isLoading={cancelMutation.isPending}>
            Cancel Request
          </Button>
        )}
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{request.title}</CardTitle>
            <StatusBadge status={request.status} />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div>
              <p className="text-xs text-gray-500">Type</p>
              <p className="text-sm font-medium text-gray-900">{request.request_type}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Stage</p>
              <p className="text-sm font-medium text-gray-900">{request.current_stage}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Priority</p>
              <p className="text-sm font-medium text-gray-900 capitalize">{request.priority}</p>
            </div>
          </div>

          <div>
            <p className="text-xs text-gray-500">Summary</p>
            <p className="mt-1 text-sm text-gray-700">{request.summary}</p>
          </div>

          {request.final_decision && (
            <Alert variant="success" title="Decision">
              {request.final_decision}
            </Alert>
          )}
        </CardContent>
      </Card>
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
