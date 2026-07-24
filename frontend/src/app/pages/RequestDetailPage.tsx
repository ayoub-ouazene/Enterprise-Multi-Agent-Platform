import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, AlertTriangle, Calendar, Clock, Tag, User, CheckCircle,
  MessageSquare, RefreshCw, Power, Send, ChevronRight
} from 'lucide-react';
import { PageContainer } from '../../components/layout/PageContainer';
import { Section } from '../../components/layout/PageContainer';
import { RequestStatusBadge } from '../../components/request/RequestStatusBadge';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { Button } from '../../components/ui/Button';
import { Alert } from '../../components/ui/Alert';
import { EmptyState } from '../../components/ui/EmptyState';
import { useRequest, useCancelRequest } from '../../api/hooks/useRequests';
import { useWorkflowEvents } from '../../api/hooks/useWorkflowEvents';
import { useWorkflowControl } from '../../api/hooks/useWorkflowControl';
import { useRequestSse } from '../../api/hooks/useRequestSse';
import { useAuthContext } from '../../auth/hooks/useAuthContext';
import { isCompanyAccount, isDepartmentManager } from '../../auth/permissions';
import { formatDateTime, relativeTime } from '../../lib/formatters';
import { getRequestStatusMeta } from '../../lib/status';
import type { WorkflowEvent } from '../../api/types';

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'timeline', label: 'Timeline' },
] as const;

type TabKey = typeof TABS[number]['key'];

export function RequestDetailPage() {
  const { requestId = '' } = useParams();
  const navigate = useNavigate();
  const { user } = useAuthContext();
  const [activeTab, setActiveTab] = useState<TabKey>('overview');

  const { data: request, isLoading, error } = useRequest(requestId);
  const cancelMutation = useCancelRequest();
  const control = useWorkflowControl(requestId);

  useRequestSse(requestId);

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
    try { await cancelMutation.mutateAsync(requestId); } catch { /* ignore */ }
  };

  const terminal = ['completed', 'rejected', 'cancelled', 'failed'];
  const canCancel = ['created', 'routing', 'processing'].includes(request.status);
  const isResolved = terminal.includes(request.status);
  const isManager = isCompanyAccount(user) || isDepartmentManager(user);

  const ws = request.workflow_state as Record<string, any>;
  const needsClarification = ws?.routing?.needs_clarification === true;
  const clarificationQuestion = ws?.routing?.latest_question as string | undefined;

  return (
    <PageContainer>
      {/* Top bar */}
      <div className="mb-6 flex items-center justify-between">
        <Button variant="ghost" onClick={() => navigate('/app/requests')}>
          <ArrowLeft size={16} className="mr-1.5" aria-hidden="true" />
          Back
        </Button>
        <div className="flex items-center gap-2">
          {needsClarification && (
            <span className="inline-flex items-center gap-1 rounded-full bg-warning-50 px-2.5 py-0.5 text-xs font-medium text-warning-700 dark:bg-warning-900 dark:text-warning-200">
              <MessageSquare size={12} />
              Needs clarification
            </span>
          )}
          {canCancel && (
            <Button variant="danger" size="sm" onClick={handleCancel} isLoading={cancelMutation.isPending}>
              Cancel
            </Button>
          )}
          {isManager && !isResolved && request.status === 'created' && (
            <Button size="sm" onClick={() => control.start.mutate()} isLoading={control.start.isPending}>
              <Power size={14} className="mr-1" />
              Start
            </Button>
          )}
          {isManager && !isResolved && request.status !== 'created' && !needsClarification && (
            <Button size="sm" variant="secondary" onClick={() => control.resume.mutate()} isLoading={control.resume.isPending}>
              <RefreshCw size={14} className="mr-1" />
              Resume
            </Button>
          )}
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 sm:text-2xl">
            {request.title}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-neutral-500 dark:text-neutral-400">
            <span className="inline-flex items-center gap-1"><Tag size={14} aria-hidden="true" />{request.request_type}</span>
            <span className="inline-flex items-center gap-1"><Calendar size={14} aria-hidden="true" />{formatDateTime(request.created_at)}</span>
          </div>
        </div>
        <RequestStatusBadge status={request.status} />
      </div>

      {/* Tabs */}
      <div className="mt-6 border-b border-neutral-200 dark:border-neutral-800" role="tablist" aria-label="Request tabs">
        <div className="flex gap-4">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              role="tab"
              aria-selected={activeTab === tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`border-b-2 pb-2 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'border-primary-600 text-primary-600 dark:border-primary-400 dark:text-primary-400'
                  : 'border-transparent text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="mt-4">
        {activeTab === 'overview' && (
          <OverviewTab
            request={request}
            isResolved={isResolved}
            needsClarification={needsClarification}
            clarificationQuestion={clarificationQuestion}
            onClarify={(answer) => control.clarify.mutate(answer)}
            isClarifying={control.clarify.isPending}
          />
        )}
        {activeTab === 'timeline' && (
          <TimelineTab requestId={requestId} />
        )}
      </div>
    </PageContainer>
  );
}

function OverviewTab({
  request,
  isResolved,
  needsClarification,
  clarificationQuestion,
  onClarify,
  isClarifying,
}: {
  request: any;
  isResolved: boolean;
  needsClarification: boolean;
  clarificationQuestion?: string;
  onClarify: (answer: string) => void;
  isClarifying: boolean;
}) {
  const [clarifyInput, setClarifyInput] = useState('');

  return (
    <div className="space-y-6">
      {/* Meta grid */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetaTile icon={<Tag size={16} />} label="Type" value={request.request_type} />
        <MetaTile icon={<Clock size={16} />} label="Stage" value={request.current_stage} />
        <MetaTile icon={<AlertTriangle size={16} />} label="Priority" value={<span className="capitalize">{request.priority}</span>} />
        <MetaTile icon={<User size={16} />} label="Status" value={<RequestStatusBadge status={request.status} />} />
      </div>

      {/* Clarification banner */}
      {needsClarification && clarificationQuestion && (
        <Alert variant="warning" title="Clarification needed">
          <div className="space-y-3">
            <p className="text-sm">{clarificationQuestion}</p>
            <div className="flex gap-2">
              <input
                type="text"
                value={clarifyInput}
                onChange={(e) => setClarifyInput(e.target.value)}
                placeholder="Your answer..."
                className="flex-1 rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100"
                onKeyDown={(e) => { if (e.key === 'Enter' && clarifyInput.trim()) onClarify(clarifyInput.trim()); }}
              />
              <Button size="sm" onClick={() => clarifyInput.trim() && onClarify(clarifyInput.trim())} isLoading={isClarifying}>
                <Send size={14} className="mr-1" />
                Submit
              </Button>
            </div>
          </div>
        </Alert>
      )}

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
          {request.final_reason && (
            <p className="mt-1 text-sm opacity-90">{request.final_reason}</p>
          )}
        </Alert>
      )}

      {/* Failure reason */}
      {request.status === 'failed' && request.final_reason && (
        <Alert variant="error" title="Request failed">
          {request.final_reason}
        </Alert>
      )}
    </div>
  );
}

function TimelineTab({ requestId }: { requestId: string }) {
  const { data: events, isLoading, error } = useWorkflowEvents(requestId);

  if (isLoading) return <LoadingSpinner />;
  if (error) return <Alert variant="error">Failed to load timeline.</Alert>;
  if (!events || events.length === 0) {
    return <EmptyState title="No events yet" description="Workflow events will appear here as the request progresses." />;
  }

  return (
    <div className="relative space-y-4">
      {/* vertical line */}
      <div className="absolute left-3.5 top-2 bottom-2 w-px bg-neutral-200 dark:bg-neutral-700" aria-hidden="true" />
      {events.map((event: WorkflowEvent) => (
        <TimelineEventItem key={event.id} event={event} />
      ))}
    </div>
  );
}

function TimelineEventItem({ event }: { event: WorkflowEvent }) {
  const icon = eventIcon(event.event_type);
  const meta = getRequestStatusMeta(event.event_type);

  return (
    <div className="relative flex gap-4">
      <div className={`z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${meta.category === 'neutral' ? 'bg-neutral-100 dark:bg-neutral-800' : 'bg-primary-100 dark:bg-primary-900'}`}>
        <span className="text-xs text-primary-700 dark:text-primary-300">{icon}</span>
      </div>
      <div className="min-w-0 flex-1 rounded-lg border border-neutral-200 bg-white p-3 dark:border-neutral-800 dark:bg-neutral-800">
        <div className="flex items-center justify-between gap-2">
          <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{event.title}</h4>
          <span className="shrink-0 text-xs text-neutral-500 dark:text-neutral-400">{relativeTime(event.created_at)}</span>
        </div>
        <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">{event.message}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
          <span>{event.actor_label}</span>
          {event.stage && (
            <>
              <ChevronRight size={12} aria-hidden="true" />
              <span>{event.stage}</span>
            </>
          )}
        </div>
      </div>
    </div>
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

function eventIcon(eventType: string): string {
  switch (eventType) {
    case 'request_created': return 'RC';
    case 'routing_started': return 'RT';
    case 'request_routed': return 'RD';
    case 'stage_started': return 'ST';
    case 'stage_completed': return 'SC';
    case 'waiting_for_human_approval': return 'WA';
    case 'waiting_for_human_action': return 'WH';
    case 'review_started': return 'RS';
    case 'review_completed': return 'RC';
    case 'request_completed': return 'CP';
    case 'request_failed': return 'FL';
    case 'request_cancelled': return 'CN';
    case 'request_rejected': return 'RJ';
    default: return 'EV';
  }
}
