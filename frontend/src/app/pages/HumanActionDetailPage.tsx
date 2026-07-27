import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  CalendarClock,
  Link2,
  Clock,
  User,
  ShieldAlert,
} from 'lucide-react';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Skeleton } from '../../components/layout/Skeleton';
import { Alert } from '../../components/ui/Alert';
import { EmptyState } from '../../components/ui/EmptyState';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { StatusDot } from '../../components/layout/MetricCard';
import { useHumanAction, useSubmitStructuredHumanAction } from '../../api/hooks/useHumanAction';
import { useRequestSse } from '../../api/hooks/useRequestSse';
import { formatDateTime, relativeTime } from '../../lib/formatters';
import { getHumanActionStatusMeta } from '../../lib/status';
import { ApiErrorException } from '../../api/errors';
import {
  ActionTypeBadge,
  DecisionPackageView,
  ResponseForm,
  ActionHistory,
} from '../../human-action/components';

export function HumanActionDetailPage() {
  const { actionId = '' } = useParams();
  const navigate = useNavigate();
  const { data: action, isLoading, error, refetch } = useHumanAction(actionId);
  const submit = useSubmitStructuredHumanAction(actionId);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Subscribe to real-time updates for the parent request
  const requestId = action?.request_id;
  useRequestSse(requestId);

  const handleSubmit = (decision: string, fields: Record<string, unknown>) => {
    setSubmitError(null);
    submit.submit(decision, fields, {
      onError: (err: unknown) => {
        if (err instanceof ApiErrorException && err.error.status === 409) {
          setSubmitError('This action was already resolved or its facts changed. The latest information has been loaded.');
          refetch();
        } else {
          setSubmitError('The response was not confirmed. Your action remains unchanged.');
        }
      },
      onSuccess: () => {
        sessionStorage.removeItem(`tellus.action-comment.${actionId}`);
        refetch();
      },
    });
  };

  if (isLoading) {
    return (
      <PageContainer>
        <Skeleton variant="rect" className="mb-4 h-8 w-48" />
        <div className="space-y-4">
          <Skeleton variant="rect" className="h-32 w-full" />
          <Skeleton variant="rect" className="h-64 w-full" />
        </div>
      </PageContainer>
    );
  }

  if (error || !action) {
    return (
      <PageContainer>
        <EmptyState
          title="Action not found"
          description="The human action you are looking for does not exist or you do not have access."
          action={
            <Button onClick={() => navigate('/app/human-actions')}>
              Back to human actions
            </Button>
          }
        />
      </PageContainer>
    );
  }

  const meta = getHumanActionStatusMeta(action.status);
  const now = new Date();
  const overdue = action.due_date ? new Date(action.due_date) < now : false;
  const cat = overdue && action.status === 'pending' ? 'attention' : meta.category;

  return (
    <PageContainer>
      {/* Navigation */}
      <div className="mb-4">
        <Button variant="ghost" size="sm" onClick={() => navigate('/app/human-actions')}>
          <ArrowLeft size={16} className="mr-1.5" aria-hidden="true" />
          Back
        </Button>
      </div>

      <PageHeader title={action.title} description={action.description}>
        <div className="flex flex-wrap items-center gap-2">
          <ActionTypeBadge actionType={action.action_type} />
          <div className="flex items-center gap-1">
            <StatusDot category={cat} />
            <span className="text-xs font-medium uppercase tracking-wide text-neutral-600 dark:text-neutral-400">
              {meta.label}
            </span>
          </div>
          {overdue && action.status === 'pending' && (
            <Badge category="attention">Overdue</Badge>
          )}
        </div>
      </PageHeader>

      {/* Info bar */}
      <div className="mb-6 flex flex-wrap items-center gap-4 text-xs text-neutral-500 dark:text-neutral-400">
        {action.request_title && (
          <button
            onClick={() => navigate(`/app/requests/${action.request_id}`)}
            className="inline-flex items-center gap-1 text-primary-600 hover:underline dark:text-primary-400"
            title="View request"
          >
            <Link2 size={12} aria-hidden="true" />
            {action.request_title}
          </button>
        )}
        <span className="inline-flex items-center gap-1">
          <Clock size={12} aria-hidden="true" />
          {relativeTime(action.created_at)}
        </span>
        {action.due_date && (
          <span
            className={`inline-flex items-center gap-1 ${
              overdue ? 'font-semibold text-danger-600 dark:text-danger-400' : ''
            }`}
          >
            <CalendarClock size={12} aria-hidden="true" />
            Due {formatDateTime(action.due_date)}
          </span>
        )}
        {action.can_respond && (
          <span className="inline-flex items-center gap-1">
            <User size={12} aria-hidden="true" />
            Assigned to you
          </span>
        )}
        {!action.can_respond && action.status === 'pending' && (
          <span className="inline-flex items-center gap-1 text-warning-600 dark:text-warning-400">
            <ShieldAlert size={12} aria-hidden="true" />
            View only
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left: Context */}
        <div className="space-y-6 lg:col-span-2">
          {/* Decision package */}
          <section aria-labelledby="context-heading">
            <h3
              id="context-heading"
              className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Context
            </h3>
            <DecisionPackageView actionType={action.action_type} context={action.safe_context} />
          </section>

          {/* Response form */}
          {action.status === 'pending' && (
            <section
              aria-labelledby="response-heading"
              className="rounded-lg border border-neutral-200 bg-white p-5 dark:border-neutral-700 dark:bg-neutral-800"
            >
              <h3
                id="response-heading"
                className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
              >
                Response
              </h3>
              {submit.isSuccess ? (
                <Alert variant="success" title="Response submitted">
                  Your response has been recorded. The related request now shows the authoritative workflow state.
                </Alert>
              ) : (
                <ResponseForm
                  action={action}
                  onSubmit={handleSubmit}
                  isSubmitting={submit.isPending}
                />
              )}
              {submitError && (
                <Alert variant="error" title="Submission failed" className="mt-4">
                  {submitError}
                </Alert>
              )}
            </section>
          )}

          {/* History */}
          <section aria-labelledby="history-heading">
              <h3
                id="history-heading"
                className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
              >
                Response Record
              </h3>
              <ActionHistory action={action} />
              {action.status !== 'pending' && action.resolution_decision && <Alert variant="success" className="mt-4" title={`Final response: ${action.resolution_decision.replaceAll('_', ' ')}`}>{action.resolution_comment ?? 'No additional comment was recorded.'}</Alert>}
            </section>
        </div>

        {/* Right: Meta sidebar */}
        <aside className="space-y-4">
          <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-800">
            <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
              Details
            </h4>
            <dl className="mt-3 space-y-3">
              <DetailRow label="Request ID" value={action.request_id.slice(0, 8)} />
              <DetailRow label="Status" value={<span className="capitalize">{action.status}</span>} />
              <DetailRow label="Request Status" value={<span className="capitalize">{action.related_request.status.replace(/_/g, ' ')}</span>} />
              {action.requesting_department && <DetailRow label="Requested by" value={action.requesting_department} />}
              {action.assigned_role && <DetailRow label="Assigned role" value={action.assigned_role.replaceAll('_', ' ')} />}
              <DetailRow label="Created" value={formatDateTime(action.created_at)} />
              {action.updated_at !== action.created_at && (
                <DetailRow label="Updated" value={formatDateTime(action.updated_at)} />
              )}
              {action.resolved_at && (
                <DetailRow label="Resolved" value={formatDateTime(action.resolved_at)} />
              )}
            </dl>
          </div>
        </aside>
      </div>
    </PageContainer>
  );
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-neutral-500 dark:text-neutral-400">{label}</dt>
      <dd className="mt-0.5 text-sm text-neutral-900 dark:text-neutral-100">{value}</dd>
    </div>
  );
}
