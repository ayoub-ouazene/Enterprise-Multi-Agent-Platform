import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, Calendar, Clock, Tag, User, CheckCircle } from 'lucide-react';
import { PageContainer } from '../../components/layout/PageContainer';
import { Section } from '../../components/layout/PageContainer';
import { RequestStatusBadge } from '../../components/request/RequestStatusBadge';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { Button } from '../../components/ui/Button';
import { Alert } from '../../components/ui/Alert';
import { EmptyState } from '../../components/ui/EmptyState';
import { useRequest, useCancelRequest } from '../../api/hooks/useRequests';
import { formatDateTime } from '../../lib/formatters';

export function RequestDetailPage() {
  const { requestId = '' } = useParams();
  const navigate = useNavigate();
  const { data: request, isLoading, error } = useRequest(requestId);
  const cancelMutation = useCancelRequest();

  if (isLoading) return <PageContainer><LoadingSpinner /></PageContainer>;
  if (error || !request) {
    return (
      <PageContainer>
        <EmptyState
          title="Request not found"
          description="The request you are looking for does not exist."
          action={<Button onClick={() => navigate('/app/requests')}>Back to requests</Button>}
        />
      </PageContainer>
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
  const isResolved = request.status === 'completed' || request.status === 'cancelled' || request.status === 'failed';

  return (
    <PageContainer>
      <div className="mb-6 flex items-center justify-between">
        <Button variant="ghost" onClick={() => navigate('/app/requests')}>
          <ArrowLeft size={16} className="mr-1.5" aria-hidden="true" />
          Back
        </Button>
        {canCancel && (
          <Button variant="danger" onClick={handleCancel} isLoading={cancelMutation.isPending}>
            Cancel Request
          </Button>
        )}
      </div>

      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 sm:text-2xl">
              {request.title}
            </h1>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-neutral-500 dark:text-neutral-400">
              <span className="inline-flex items-center gap-1">
                <Tag size={14} aria-hidden="true" />
                {request.request_type}
              </span>
              <span className="inline-flex items-center gap-1">
                <Calendar size={14} aria-hidden="true" />
                {formatDateTime(request.created_at)}
              </span>
            </div>
          </div>
          <RequestStatusBadge status={request.status} />
        </div>

        {/* Meta grid */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetaTile icon={<Tag size={16} />} label="Type" value={request.request_type} />
          <MetaTile icon={<Clock size={16} />} label="Stage" value={request.current_stage} />
          <MetaTile icon={<AlertTriangle size={16} />} label="Priority" value={<span className="capitalize">{request.priority}</span>} />
          <MetaTile icon={<User size={16} />} label="Status" value={<RequestStatusBadge status={request.status} />} />
        </div>

        {/* Summary */}
        <Section title="Request Summary">
          <p className="leading-relaxed text-neutral-700 dark:text-neutral-300">
            {request.summary || 'No summary provided.'}
          </p>
        </Section>

        {/* Decision */}
        {request.final_decision && isResolved && (
          <Alert variant="success" title="Decision">
            <div className="flex items-center gap-2">
              <CheckCircle size={16} aria-hidden="true" />
              {request.final_decision}
            </div>
          </Alert>
        )}
      </div>
    </PageContainer>
  );
}

function MetaTile({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-800">
      <div className="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400">
        {icon}
        {label}
      </div>
      <div className="mt-2 text-sm font-medium text-neutral-900 dark:text-neutral-100">{value}</div>
    </div>
  );
}
