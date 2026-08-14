import { useEffect, useRef, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import {
  AlertTriangle, ArrowLeft, Ban, Check, CheckCircle2, Clipboard,
  Clock3, Copy, GitBranch, Hand, Info, MessageCircleQuestion, Radio,
  RefreshCw, Route, ShieldCheck, Sparkles, UserRound, XCircle,
} from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import type { BusinessRequestDetail, WorkflowEvent } from '../../api/types';
import { useCancelRequest, useRequest } from '../../api/hooks/useRequests';
import { useWorkflowControl } from '../../api/hooks/useWorkflowControl';
import { useWorkflowEvents } from '../../api/hooks/useWorkflowEvents';
import { useRequestSse } from '../../api/hooks/useRequestSse';
import { useSseConnection } from '../providers/SseProvider';
import { ApiErrorException } from '../../api/errors';
import { PageContainer } from '../../components/layout/PageContainer';
import { Skeleton } from '../../components/layout/Skeleton';
import { Alert } from '../../components/ui/Alert';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { Textarea } from '../../components/ui/FormControls';
import { RequestStatusBadge } from '../../components/request/RequestStatusBadge';
import { formatDateTime, relativeTime } from '../../lib/formatters';
import { getRequestStatusMeta, statusAccentColors } from '../../lib/status';
import { duration, easing } from '../../motion/tokens';

export function RequestDetailPage() {
  const { requestId = '' } = useParams();
  const requestQuery = useRequest(requestId);
  const eventsQuery = useWorkflowEvents(requestId);
  const workflow = useWorkflowControl(requestId);
  const started = useRef<string | null>(null);
  useRequestSse(requestId);

  useEffect(() => {
    if (requestQuery.data?.status !== 'created' || started.current === requestId) return;
    started.current = requestId;
    workflow.start.mutate(undefined, { onSettled: () => requestQuery.refetch() });
  }, [requestId, requestQuery, workflow.start]);

  if (requestQuery.isLoading) return <RequestDetailSkeleton />;
  if (requestQuery.isError || !requestQuery.data) {
    return <PageContainer><div className="mx-auto max-w-lg rounded-card border border-neutral-200 bg-white p-8 text-center shadow-card dark:border-neutral-800 dark:bg-neutral-900"><XCircle className="mx-auto text-neutral-300" size={36} /><h1 className="mt-4 text-xl font-semibold">Request unavailable</h1><p className="mt-2 text-sm text-neutral-500">It may not exist or your account may not be authorized to view it.</p><Link to="/app/requests" className="mt-5 inline-flex min-h-10 items-center font-semibold text-primary-600">Back to requests</Link></div></PageContainer>;
  }

  return <RequestWorkspace request={requestQuery.data} events={eventsQuery.data ?? []} eventsLoading={eventsQuery.isLoading} refresh={() => { requestQuery.refetch(); eventsQuery.refetch(); }} />;
}

function RequestWorkspace({ request, events, eventsLoading, refresh }: { request: BusinessRequestDetail; events: WorkflowEvent[]; eventsLoading: boolean; refresh: () => void }) {
  const shortId = request.id.slice(0, 8).toUpperCase();
  const status = getRequestStatusMeta(request.status);
  const [cancelOpen, setCancelOpen] = useState(false);
  const cancel = useCancelRequest();
  const [cancelError, setCancelError] = useState<string | null>(null);
  const { connected } = useSseConnection();

  const confirmCancel = async () => {
    setCancelError(null);
    try {
      await cancel.mutateAsync(request.id);
      setCancelOpen(false);
    } catch (error) {
      setCancelError(error instanceof ApiErrorException && error.error.code === 'CONFLICT' ? 'The request changed and can no longer be cancelled. The current state has been refreshed.' : 'Cancellation could not be confirmed. The request remains unchanged.');
      refresh();
    }
  };

  return <PageContainer className="space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-3"><Link to="/app/requests" className="inline-flex min-h-10 items-center text-sm font-semibold text-neutral-600 hover:text-primary-700 dark:text-neutral-300"><ArrowLeft size={16} className="mr-2" />All requests</Link><div className="flex items-center gap-2"><span role="status" className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-medium ${connected ? 'bg-success-50 text-success-700 dark:bg-success-950 dark:text-success-300' : 'bg-warning-50 text-warning-800 dark:bg-warning-950 dark:text-warning-200'}`}><span className={`h-2 w-2 rounded-full ${connected ? 'bg-success-500' : 'bg-warning-500'}`} />{connected ? 'Live updates on' : 'Showing last update'}</span><Button variant="ghost" size="sm" onClick={refresh} aria-label="Refresh request"><RefreshCw size={15} /></Button></div></div>

    <header className="border-b border-neutral-200 pb-6 dark:border-neutral-800"><div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[.12em] text-neutral-500"><span>Request {shortId}</span><button type="button" onClick={() => navigator.clipboard.writeText(request.id)} aria-label={`Copy full Request ID ${shortId}`} className="rounded p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800"><Copy size={13} /></button></div><h1 className="mt-2 text-2xl font-bold tracking-tight text-neutral-950 sm:text-3xl dark:text-white">{request.title}</h1><p className="mt-2 max-w-3xl text-sm text-neutral-500">{request.request_type.replaceAll('_', ' ')} · Created {formatDateTime(request.created_at)}</p></div><div className="flex shrink-0 flex-wrap items-center gap-2"><RequestStatusBadge status={request.status} />{request.can_cancel && <Button size="sm" variant="danger" onClick={() => setCancelOpen(true)}>Cancel request</Button>}</div></div></header>

    <CurrentState request={request} status={status} />
    {request.clarification && <ClarificationPanel request={request} refresh={refresh} />}
    <ConnectedActions actions={request.connected_actions} />

    <div className="grid items-start gap-8 xl:grid-cols-[minmax(0,1fr)_21rem]">
      <div className="space-y-8">
        {request.final_result && <FinalResult request={request} />}
        {request.failure_summary && <FailurePanel request={request} />}
        <Timeline events={events} loading={eventsLoading} />
      </div>
      <aside className="space-y-5 xl:sticky xl:top-6">
        <Metadata request={request} />
        <section className="rounded-card border border-neutral-200 bg-white p-5 shadow-xs dark:border-neutral-800 dark:bg-neutral-900"><h2 className="font-semibold text-neutral-950 dark:text-white">Request details</h2><p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-neutral-600 dark:text-neutral-300">{request.summary}</p></section>
      </aside>
    </div>

    <Modal title="Cancel this request?" isOpen={cancelOpen} onClose={() => !cancel.isPending && setCancelOpen(false)}><div className="space-y-4"><p className="text-sm leading-6 text-neutral-600 dark:text-neutral-300">Cancellation stops future workflow processing. Work already completed cannot be undone, and the backend will reject cancellation if the request has advanced to an irreversible state.</p>{cancelError && <Alert variant="error">{cancelError}</Alert>}<div className="flex justify-end gap-2"><Button variant="secondary" disabled={cancel.isPending} onClick={() => setCancelOpen(false)}>Keep request</Button><Button variant="danger" isLoading={cancel.isPending} onClick={confirmCancel}>Confirm cancellation</Button></div></div></Modal>
  </PageContainer>;
}

function CurrentState({ request, status }: { request: BusinessRequestDetail; status: ReturnType<typeof getRequestStatusMeta> }) {
  const reduced = useReducedMotion();
  const owner = request.owner_department?.name;
  const assistant = request.active_department && request.active_department.id !== request.owner_department?.id ? request.active_department.name : null;
  return <motion.section key={request.status} initial={reduced ? false : { opacity: .7 }} animate={{ opacity: 1 }} transition={{ duration: reduced ? 0 : duration.normal }} className="relative overflow-hidden rounded-card border border-neutral-200 bg-white p-5 shadow-card sm:p-6 dark:border-neutral-800 dark:bg-neutral-900" aria-live="polite"><span className={`absolute inset-y-0 left-0 w-1 ${statusAccentColors[status.category]}`} /><div className="flex items-start gap-4"><span className="metric-icon flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-indigo-500 dark:text-indigo-400">{stateIcon(request.status)}</span><div className="min-w-0"><p className="text-xs font-semibold uppercase tracking-[.12em] text-neutral-500">What is happening now</p><h2 className="mt-1 text-lg font-semibold text-neutral-950 dark:text-white">{status.label}</h2><p className="mt-1 text-sm leading-6 text-neutral-600 dark:text-neutral-300">{request.current_state_summary}</p><div className="mt-3 flex flex-wrap gap-2">{owner && <Badge variant="neutral">Owner: {owner}</Badge>}{assistant && <Badge variant="info">Assisting: {assistant}</Badge>}{request.quality_check_summary && <Badge variant="info">Quality check</Badge>}</div>{request.collaboration_summary && <p className="mt-3 text-sm text-neutral-500">{request.collaboration_summary}</p>}{request.quality_check_summary && <p className="mt-2 text-sm text-neutral-500">{request.quality_check_summary}</p>}</div></div></motion.section>;
}

function ClarificationPanel({ request, refresh }: { request: BusinessRequestDetail; refresh: () => void }) {
  const workflow = useWorkflowControl(request.id);
  const key = `orchestra.clarification.${request.id}`;
  const submissionInFlight = useRef(false);
  const [answer, setAnswer] = useState(() => sessionStorage.getItem(key) ?? '');
  const [message, setMessage] = useState<string | null>(null);
  const submit = async () => {
    if (!answer.trim() || submissionInFlight.current || workflow.clarify.isPending) return;
    submissionInFlight.current = true;
    setMessage(null);
    try {
      await workflow.clarify.mutateAsync(answer.trim());
      sessionStorage.removeItem(key);
      setAnswer('');
      setMessage('Your answer was confirmed. Processing is resuming.');
    } catch (error) {
      setMessage(error instanceof ApiErrorException && error.error.code === 'CONFLICT' ? 'This clarification was already answered or the request changed. Refreshing the request.' : 'The server did not confirm the answer. It remains saved while the latest request state loads.');
      refresh();
    } finally {
      submissionInFlight.current = false;
    }
  };
  return <motion.section initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} className="rounded-card border border-warning-300 bg-warning-50 p-5 shadow-card dark:border-warning-900 dark:bg-warning-950/40" aria-labelledby="clarification-title"><div className="flex gap-3"><MessageCircleQuestion className="mt-0.5 shrink-0 text-warning-700" size={22} /><div className="min-w-0 flex-1"><p className="text-xs font-semibold uppercase tracking-wide text-warning-700">Required action · Question {request.clarification?.number} of {request.clarification?.maximum}</p><h2 id="clarification-title" className="mt-1 font-semibold text-warning-950 dark:text-warning-100">More information is required</h2><p className="mt-2 text-sm leading-6 text-warning-900 dark:text-warning-200">{request.clarification?.question}</p><div className="mt-4"><Textarea label="Your answer" value={answer} autoFocus onChange={(event) => { setAnswer(event.target.value); sessionStorage.setItem(key, event.target.value); }} aria-describedby="clarification-help" /><p id="clarification-help" className="mt-1.5 text-xs text-warning-700">Processing resumes only after the server confirms your answer.</p></div>{message && <p className="mt-3 text-sm" role="status">{message}</p>}<Button className="mt-4" onClick={submit} isLoading={workflow.clarify.isPending} disabled={!answer.trim()}>Submit answer</Button></div></div></motion.section>;
}

function ConnectedActions({ actions }: { actions: BusinessRequestDetail['connected_actions'] }) {
  if (!actions.length) return null;
  return <section aria-labelledby="connected-actions"><h2 id="connected-actions" className="mb-3 font-semibold text-neutral-950 dark:text-white">Connected HumanActions</h2><div className="grid gap-3 sm:grid-cols-2">{actions.map((action) => <article key={action.id} className="rounded-card border border-neutral-200 bg-white p-4 shadow-xs dark:border-neutral-800 dark:bg-neutral-900"><div className="flex items-start gap-3"><span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${action.status === 'pending' ? 'bg-warning-50 text-warning-700 dark:bg-warning-950' : 'bg-success-50 text-success-700 dark:bg-success-950'}`}><Hand size={17} /></span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h3 className="font-medium text-neutral-950 dark:text-white">{action.title}</h3><Badge variant={action.status === 'pending' ? 'warning' : 'success'}>{action.status === 'pending' ? 'Waiting' : 'Resolved'}</Badge></div><p className="mt-1 text-xs text-neutral-500">{safeActionLabel(action.action_type)}{action.due_at ? ` · Due ${formatDateTime(action.due_at)}` : ''}</p>{action.assigned_role && <p className="mt-1 text-xs text-neutral-500">Assigned role: {action.assigned_role.replaceAll('_', ' ')}</p>}{action.can_respond && action.action_url && <Link to={action.action_url} className="mt-3 inline-flex min-h-9 items-center text-sm font-semibold text-primary-600">Open assigned action</Link>}</div></div></article>)}</div></section>;
}

function Timeline({ events, loading }: { events: WorkflowEvent[]; loading: boolean }) {
  if (loading) return <section><h2 className="mb-4 font-semibold">Workflow timeline</h2><div className="space-y-4">{Array.from({ length: 4 }, (_, index) => <div key={index} className="flex gap-3"><Skeleton className="h-8 w-8 rounded-full" /><Skeleton className="h-20 flex-1 rounded-card" /></div>)}</div></section>;
  return <section aria-labelledby="timeline-title"><div className="mb-4 flex items-center justify-between"><div><h2 id="timeline-title" className="font-semibold text-neutral-950 dark:text-white">Workflow timeline</h2><p className="mt-1 text-sm text-neutral-500">Persisted, requester-safe milestones.</p></div></div>{events.length ? <ol className="relative space-y-4 before:absolute before:bottom-4 before:left-[15px] before:top-4 before:w-[3px] before:rounded-full before:bg-gradient-to-b before:from-indigo-500/60 before:via-violet-500/40 before:to-cyan-500/25 before:shadow-[0_0_12px_rgba(99,102,241,0.35)] dark:before:from-indigo-400/70 dark:before:via-violet-400/45 dark:before:to-cyan-400/30">{events.map((event, index) => <TimelineItem key={event.id} event={event} current={index === events.length - 1} />)}</ol> : <div className="rounded-card border border-dashed border-neutral-300 p-8 text-center text-sm text-neutral-500 dark:border-neutral-700">Workflow milestones will appear after routing begins.</div>}</section>;
}

function TimelineItem({ event, current }: { event: WorkflowEvent; current: boolean }) {
  const reduced = useReducedMotion();
  return <motion.li initial={reduced ? false : { opacity: 0, y: 3 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduced ? 0 : duration.fast, ease: easing.easeOut }} className="relative flex gap-4"><span className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-4 border-neutral-50 dark:border-neutral-950 ${current ? 'bg-primary-600 text-white' : 'bg-neutral-200 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300'}`}>{eventIcon(event.event_type)}</span><div className={`min-w-0 flex-1 rounded-card border p-4 ${current ? 'border-primary-200 bg-primary-50/40 dark:border-primary-900 dark:bg-primary-950/20' : 'border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900'}`}><div className="flex flex-wrap items-start justify-between gap-2"><h3 className="text-sm font-semibold text-neutral-950 dark:text-white">{event.title}</h3><time className="text-xs text-neutral-400" dateTime={event.created_at}>{relativeTime(event.created_at)}</time></div><p className="mt-1 text-sm leading-6 text-neutral-600 dark:text-neutral-300">{event.message}</p></div></motion.li>;
}

function FinalResult({ request }: { request: BusinessRequestDetail }) {
  const result = request.final_result!;
  return <motion.section initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="rounded-card border border-success-200 bg-success-50/60 p-5 shadow-card sm:p-6 dark:border-success-900 dark:bg-success-950/25"><div className="flex items-start gap-3"><CheckCircle2 className="shrink-0 text-success-600" size={24} /><div className="min-w-0 flex-1"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-success-700">Final result</p><h2 className="mt-1 text-lg font-semibold text-success-950 dark:text-success-100">{result.title}</h2></div><Button variant="secondary" size="sm" onClick={() => navigator.clipboard.writeText(result.summary)} aria-label="Copy final result"><Clipboard size={14} className="mr-2" />Copy</Button></div><p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-success-900 dark:text-success-200">{result.summary}</p>{result.limitations.length > 0 && <ResultList title="Limitations" items={result.limitations} />}{result.next_steps.length > 0 && <ResultList title="Next steps" items={result.next_steps} />}{result.sources.length > 0 && <div className="mt-5 border-t border-success-200 pt-4 dark:border-success-900"><h3 className="text-sm font-semibold">Sources</h3><ul className="mt-2 space-y-2">{result.sources.map((source, index) => <li key={`${source.document_id}-${index}`} className="text-sm"><span className="font-medium">{source.title}</span>{source.version && <span className="text-success-700"> · Version {source.version}</span>}{source.section && <span className="text-success-700"> · {source.section}</span>}</li>)}</ul></div>}</div></div></motion.section>;
}

function FailurePanel({ request }: { request: BusinessRequestDetail }) {
  return <section className="rounded-card border border-danger-200 bg-danger-50 p-5 dark:border-danger-900 dark:bg-danger-950/30"><div className="flex gap-3"><AlertTriangle className="shrink-0 text-danger-600" size={22} /><div><h2 className="font-semibold text-danger-950 dark:text-danger-100">{request.status === 'rejected' ? 'Request not approved' : 'Request could not be completed'}</h2><p className="mt-2 text-sm leading-6 text-danger-800 dark:text-danger-200">{request.failure_summary}</p><Link to="/app/requests/new" className="mt-3 inline-flex min-h-9 items-center text-sm font-semibold text-danger-800 dark:text-danger-200">Create a new request</Link></div></div></section>;
}

function Metadata({ request }: { request: BusinessRequestDetail }) {
  return <section className="rounded-card border border-neutral-200 bg-white p-5 shadow-xs dark:border-neutral-800 dark:bg-neutral-900"><h2 className="font-semibold text-neutral-950 dark:text-white">Metadata</h2><dl className="mt-4 space-y-3 text-sm"><Meta label="Status" value={getRequestStatusMeta(request.status).label} /><Meta label="Owner department" value={request.owner_department?.name ?? 'Routing in progress'} />{request.active_department && request.active_department.id !== request.owner_department?.id && <Meta label="Currently assisting" value={request.active_department.name} />}<Meta label="Priority" value={request.priority} />{request.requester_label && <Meta label="Requester" value={request.requester_label} />}<Meta label="Created" value={formatDateTime(request.created_at)} /><Meta label="Last updated" value={formatDateTime(request.updated_at)} /></dl></section>;
}

function Meta({ label, value }: { label: string; value: string }) {
  return <div className="flex items-start justify-between gap-4"><dt className="text-neutral-500">{label}</dt><dd className="text-right font-medium capitalize text-neutral-900 dark:text-white">{value}</dd></div>;
}

function ResultList({ title, items }: { title: string; items: string[] }) {
  return <div className="mt-4"><h3 className="text-sm font-semibold">{title}</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{items.map((item) => <li key={item}>{item}</li>)}</ul></div>;
}

function safeActionLabel(value: string) {
  const labels: Record<string, string> = { information_request: 'Information requested', identity_verification: 'Identity verification', technician_action: 'Manual technical work', supplier_selection: 'Authorized supplier selection', onboarding_confirmation: 'Onboarding confirmation' };
  return labels[value] ?? 'Authorized action';
}

function stateIcon(status: string) {
  if (status === 'routing') return <Route size={20} />;
  if (status === 'waiting_for_department') return <GitBranch size={20} />;
  if (status === 'waiting_for_human_approval') return <ShieldCheck size={20} />;
  if (status === 'waiting_for_human_action') return <Hand size={20} />;
  if (status === 'under_review') return <Sparkles size={20} />;
  if (status === 'completed') return <CheckCircle2 size={20} />;
  if (status === 'failed' || status === 'rejected') return <AlertTriangle size={20} />;
  if (status === 'cancelled') return <Ban size={20} />;
  if (status === 'created') return <Radio size={20} />;
  return <Clock3 size={20} />;
}

function eventIcon(type: string) {
  if (type === 'request_created') return <Check size={13} />;
  if (type === 'routing_started' || type === 'request_routed') return <Route size={13} />;
  if (type.includes('collaboration')) return <GitBranch size={13} />;
  if (type.includes('human')) return <UserRound size={13} />;
  if (type.includes('review')) return <ShieldCheck size={13} />;
  if (type === 'request_completed') return <CheckCircle2 size={13} />;
  if (type === 'request_failed' || type === 'request_rejected') return <AlertTriangle size={13} />;
  if (type === 'request_cancelled') return <Ban size={13} />;
  return <Info size={13} />;
}

function RequestDetailSkeleton() {
  return <PageContainer><div role="status" aria-label="Loading request" className="space-y-6"><Skeleton className="h-4 w-28" /><div><Skeleton className="h-8 w-3/5" /><Skeleton className="mt-3 h-4 w-72" /></div><Skeleton className="h-40 rounded-card" /><div className="grid gap-8 xl:grid-cols-[1fr_21rem]"><div className="space-y-4">{Array.from({ length: 4 }, (_, index) => <Skeleton key={index} className="h-24 rounded-card" />)}</div><Skeleton className="h-72 rounded-card" /></div></div></PageContainer>;
}
