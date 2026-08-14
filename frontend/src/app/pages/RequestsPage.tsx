import { useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Copy, Filter, Plus, Search, SlidersHorizontal } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { ActorType, RequestStatus, type BusinessRequestSummary } from '../../api/types';
import { useRequests, type RequestFilters } from '../../api/hooks/useRequests';
import { useAuthContext } from '../../auth/hooks/useAuthContext';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Skeleton } from '../../components/layout/Skeleton';
import { Alert } from '../../components/ui/Alert';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Checkbox, Select } from '../../components/ui/FormControls';
import { Modal } from '../../components/ui/Modal';
import { RequestStatusBadge } from '../../components/request/RequestStatusBadge';
import { relativeTime } from '../../lib/formatters';
import { getRequestStatusMeta } from '../../lib/status';
import { duration, easing } from '../../motion/tokens';

const PAGE_SIZE = 25;
const statusOptions = Object.values(RequestStatus);

export function RequestsPage() {
  const { user } = useAuthContext();
  const [params, setParams] = useSearchParams();
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [searchDraft, setSearchDraft] = useState(params.get('search') ?? '');
  const page = Math.max(1, Number(params.get('page') ?? '1') || 1);
  const canSeeRequester = user?.actor_type === ActorType.COMPANY || user?.actor_type === ActorType.DEPARTMENT_MANAGER;

  const filters: RequestFilters = {
    search: params.get('search') || undefined,
    status: params.get('status') || undefined,
    request_type: params.get('request_type') || undefined,
    owner_department_id: params.get('owner_department_id') || undefined,
    requester_user_id: canSeeRequester ? params.get('requester_user_id') || undefined : undefined,
    attention_required: params.get('attention') === 'true' ? true : undefined,
    created_from: dateBoundary(params.get('from'), false),
    created_to: dateBoundary(params.get('to'), true),
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  };
  const query = useRequests(filters);
  const requests = query.data ?? [];
  const activeFilterCount = ['search', 'status', 'request_type', 'owner_department_id', 'requester_user_id', 'attention', 'from', 'to'].filter((key) => params.has(key)).length;
  const departments = uniqueOptions(requests, (item) => item.owner_department?.id, (item) => item.owner_department?.name);
  const requesters = uniqueOptions(requests, (item) => item.requester_user_id, (item) => item.requester_label);

  const update = (key: string, value?: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    next.delete('page');
    setParams(next);
  };
  const setPage = (nextPage: number) => {
    const next = new URLSearchParams(params);
    if (nextPage <= 1) next.delete('page'); else next.set('page', String(nextPage));
    setParams(next);
  };
  const clear = () => {
    setSearchDraft('');
    setParams({});
  };

  return <PageContainer className="space-y-6">
    <PageHeader title="Business requests" description="Create, follow, and act on authorized company work.">
      <Link to="/app/requests/new" className="inline-flex h-10 items-center justify-center rounded-md bg-primary-600 px-4 text-sm font-medium text-white hover:bg-primary-700"><Plus size={16} className="mr-2" />Create request</Link>
    </PageHeader>

    <div className="flex flex-col gap-3 rounded-card border border-neutral-200 bg-white p-4 shadow-xs dark:border-neutral-800 dark:bg-neutral-900 lg:flex-row lg:items-end">
      <form className="flex min-w-0 flex-1 gap-2" onSubmit={(event) => { event.preventDefault(); update('search', searchDraft.trim() || undefined); }}>
        <label className="relative block min-w-0 flex-1"><span className="sr-only">Search requests</span><Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" /><input value={searchDraft} onChange={(event) => setSearchDraft(event.target.value)} placeholder="Search title, description, or type" className="h-10 w-full rounded-lg border border-neutral-300 bg-white pl-9 pr-3 text-sm dark:border-neutral-700 dark:bg-neutral-950" /></label>
        <Button type="submit" variant="secondary">Search</Button>
      </form>
      <div className="hidden items-end gap-3 lg:flex">
        <FilterControls params={params} update={update} departments={departments} requesters={requesters} canSeeRequester={canSeeRequester} />
      </div>
      <Button variant="secondary" className="lg:hidden" onClick={() => setFiltersOpen(true)}><SlidersHorizontal size={16} className="mr-2" />Filters{activeFilterCount > 0 ? ` (${activeFilterCount})` : ''}</Button>
    </div>

    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-neutral-500" aria-live="polite">{query.isFetching && !query.isLoading ? 'Refreshing…' : `${requests.length} result${requests.length === 1 ? '' : 's'} on this page`}</p>
      {activeFilterCount > 0 && <Button variant="ghost" size="sm" onClick={clear}>Clear {activeFilterCount} filter{activeFilterCount === 1 ? '' : 's'}</Button>}
    </div>

    {query.isError && <Alert variant="error" title="Requests are unavailable"><div className="flex flex-wrap items-center justify-between gap-3"><span>We could not load the latest request list.</span><Button size="sm" variant="secondary" onClick={() => query.refetch()}>Retry</Button></div></Alert>}
    {query.isLoading ? <RequestListSkeleton /> : requests.length ? <RequestResults requests={requests} canSeeRequester={canSeeRequester} /> : <RequestEmpty filtered={activeFilterCount > 0} attentionOnly={params.get('attention') === 'true'} clear={clear} />}

    {!query.isLoading && (page > 1 || requests.length === PAGE_SIZE) && <nav className="flex items-center justify-between border-t border-neutral-200 pt-4 dark:border-neutral-800" aria-label="Request pages"><Button variant="secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button><span className="text-sm text-neutral-500">Page {page}</span><Button variant="secondary" disabled={requests.length < PAGE_SIZE} onClick={() => setPage(page + 1)}>Next</Button></nav>}

    <Modal title="Filter requests" isOpen={filtersOpen} onClose={() => setFiltersOpen(false)}><div className="grid gap-4"><FilterControls params={params} update={update} departments={departments} requesters={requesters} canSeeRequester={canSeeRequester} /><div className="flex justify-end gap-2"><Button variant="ghost" onClick={clear}>Clear filters</Button><Button onClick={() => setFiltersOpen(false)}>Show results</Button></div></div></Modal>
  </PageContainer>;
}

function FilterControls({ params, update, departments, requesters, canSeeRequester }: { params: URLSearchParams; update: (key: string, value?: string) => void; departments: { value: string; label: string }[]; requesters: { value: string; label: string }[]; canSeeRequester: boolean }) {
  return <>
    <Select label="Status" value={params.get('status') ?? ''} onChange={(event) => update('status', event.target.value || undefined)}><option value="">All statuses</option>{statusOptions.map((status) => <option key={status} value={status}>{getRequestStatusMeta(status).label}</option>)}</Select>
    <label className="grid gap-1.5 text-sm font-medium text-neutral-700 dark:text-neutral-300">Request type<input value={params.get('request_type') ?? ''} onChange={(event) => update('request_type', event.target.value || undefined)} placeholder="Any type" className="h-10 rounded-lg border border-neutral-300 bg-white px-3 text-sm dark:border-neutral-700 dark:bg-neutral-950" /></label>
    <Select label="Owner department" value={params.get('owner_department_id') ?? ''} onChange={(event) => update('owner_department_id', event.target.value || undefined)}><option value="">All departments</option>{departments.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</Select>
    {canSeeRequester && <Select label="Requester" value={params.get('requester_user_id') ?? ''} onChange={(event) => update('requester_user_id', event.target.value || undefined)}><option value="">All requesters</option>{requesters.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</Select>}
    <label className="grid gap-1.5 text-sm font-medium text-neutral-700 dark:text-neutral-300">Created after<input type="date" value={params.get('from') ?? ''} onChange={(event) => update('from', event.target.value || undefined)} className="h-10 rounded-lg border border-neutral-300 bg-white px-3 dark:border-neutral-700 dark:bg-neutral-950" /></label>
    <label className="grid gap-1.5 text-sm font-medium text-neutral-700 dark:text-neutral-300">Created before<input type="date" value={params.get('to') ?? ''} onChange={(event) => update('to', event.target.value || undefined)} className="h-10 rounded-lg border border-neutral-300 bg-white px-3 dark:border-neutral-700 dark:bg-neutral-950" /></label>
    <Checkbox label="Attention required" checked={params.get('attention') === 'true'} onChange={(event) => update('attention', event.target.checked ? 'true' : undefined)} />
  </>;
}

function RequestResults({ requests, canSeeRequester }: { requests: BusinessRequestSummary[]; canSeeRequester: boolean }) {
  const reduced = useReducedMotion();
  return <>
    <div className="hidden overflow-hidden rounded-card border border-neutral-200 bg-white shadow-card dark:border-neutral-800 dark:bg-neutral-900 md:block"><table className="w-full table-fixed"><thead className="bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500 dark:bg-neutral-800/60"><tr><th className="w-[34%] px-4 py-3">Request</th><th className="w-[17%] px-4 py-3">Status</th><th className="w-[18%] px-4 py-3">Owner</th>{canSeeRequester && <th className="w-[16%] px-4 py-3">Requester</th>}<th className="px-4 py-3">Updated</th></tr></thead><tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">{requests.map((request, index) => <motion.tr key={request.id} initial={reduced ? false : { opacity: 0, y: 3 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduced ? 0 : duration.fast, delay: reduced ? 0 : Math.min(index, 5) * .025, ease: easing.easeOut }} className="row-hover group"><td className="px-4 py-4"><RequestIdentity request={request} /></td><td className="px-4 py-4"><RequestStatusBadge status={request.status} /><p className="mt-1 line-clamp-2 text-xs text-neutral-500">{request.current_state_summary}</p>{request.attention_required && <p className="mt-1 text-xs font-medium text-warning-700">Attention required</p>}</td><td className="truncate px-4 py-4 text-sm text-neutral-600 dark:text-neutral-300">{request.owner_department?.name ?? 'Routing'}</td>{canSeeRequester && <td className="truncate px-4 py-4 text-sm text-neutral-500">{request.requester_label ?? 'Requester'}</td>}<td className="px-4 py-4 text-sm text-neutral-500"><Link to={`/app/requests/${request.id}`} className="font-medium text-neutral-700 hover:text-primary-700 dark:text-neutral-200">{relativeTime(request.updated_at)}</Link></td></motion.tr>)}</tbody></table></div>
    <div className="grid gap-3 md:hidden">{requests.map((request) => <article key={request.id} className="row-hover rounded-card border border-neutral-200 bg-white p-4 shadow-card dark:border-neutral-800 dark:bg-neutral-900"><div className="flex items-start justify-between gap-3"><RequestIdentity request={request} /><RequestStatusBadge status={request.status} /></div><p className="mt-3 text-sm leading-5 text-neutral-500">{request.current_state_summary}</p><dl className="mt-4 grid grid-cols-2 gap-3 border-t border-neutral-100 pt-3 text-xs dark:border-neutral-800"><div><dt className="text-neutral-400">Owner</dt><dd className="mt-1 font-medium">{request.owner_department?.name ?? 'Routing'}</dd></div><div><dt className="text-neutral-400">Updated</dt><dd className="mt-1 font-medium">{relativeTime(request.updated_at)}</dd></div></dl><Link to={`/app/requests/${request.id}`} className="mt-4 inline-flex min-h-10 items-center font-semibold text-primary-600">Open request</Link></article>)}</div>
  </>;
}

function RequestIdentity({ request }: { request: BusinessRequestSummary }) {
  const shortId = request.id.slice(0, 8).toUpperCase();
  return <div className="min-w-0"><Link to={`/app/requests/${request.id}`} className="relative z-10 block truncate font-semibold text-neutral-950 hover:text-primary-700 dark:text-white">{request.title}</Link><div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-neutral-500"><span>{shortId}</span><button type="button" className="relative z-10 rounded p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800" aria-label={`Copy Request ID ${shortId}`} onClick={() => navigator.clipboard.writeText(request.id)}><Copy size={12} /></button><span>·</span><span>{request.request_type.replaceAll('_', ' ')}</span>{request.pending_action_count > 0 && <Badge variant="warning">{request.pending_action_count} action{request.pending_action_count === 1 ? '' : 's'}</Badge>}</div></div>;
}

function RequestListSkeleton() {
  return <div role="status" aria-label="Loading requests" className="overflow-hidden rounded-card border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">{Array.from({ length: 6 }, (_, index) => <div key={index} className="grid grid-cols-[2fr_1fr_1fr] gap-6 border-b border-neutral-100 p-4 last:border-0 dark:border-neutral-800"><div><Skeleton className="h-4 w-48" /><Skeleton className="mt-2 h-3 w-28" /></div><Skeleton className="h-6 w-24 rounded-full" /><Skeleton className="h-4 w-28" /></div>)}</div>;
}

function RequestEmpty({ filtered, attentionOnly, clear }: { filtered: boolean; attentionOnly: boolean; clear: () => void }) {
  return <div className="stagger-in rounded-card border border-dashed border-neutral-300 bg-white px-6 py-14 text-center dark:border-neutral-700 dark:bg-neutral-900"><span className="empty-float mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10"><Filter className="text-indigo-400/70" size={34} /></span><h2 className="mt-4 font-semibold text-neutral-950 dark:text-white">{attentionOnly ? 'No requests require attention' : filtered ? 'No requests match these filters' : 'No requests yet'}</h2><p className="mx-auto mt-2 max-w-md text-sm text-neutral-500">{filtered ? 'Adjust or clear the current filters to see other authorized requests.' : 'Create a request when you need help or want to start a company process.'}</p><div className="mt-5 flex justify-center gap-2">{filtered && <Button variant="secondary" onClick={clear}>Clear filters</Button>}<Link to="/app/requests/new" className="btn-primary-glow inline-flex h-10 items-center rounded-lg px-4 text-sm font-medium text-white">Create request</Link></div></div>;
}

function uniqueOptions(items: BusinessRequestSummary[], value: (item: BusinessRequestSummary) => string | null | undefined, label: (item: BusinessRequestSummary) => string | null | undefined) {
  const map = new Map<string, string>();
  for (const item of items) {
    const optionValue = value(item);
    const optionLabel = label(item);
    if (optionValue && optionLabel) map.set(optionValue, optionLabel);
  }
  return [...map].map(([optionValue, optionLabel]) => ({ value: optionValue, label: optionLabel }));
}

function dateBoundary(value: string | null, end: boolean): string | undefined {
  if (!value) return undefined;
  return `${value}T${end ? '23:59:59.999' : '00:00:00.000'}Z`;
}
