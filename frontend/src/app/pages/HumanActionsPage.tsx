import { motion, useReducedMotion } from 'framer-motion';
import { ArrowUpRight, Clock, Filter, SlidersHorizontal } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { useState } from 'react';
import { useHumanActions } from '../../api/hooks/useHumanActions';
import { useDepartments } from '../../api/hooks/useDepartments';
import type { HumanActionSummary } from '../../api/types';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Skeleton } from '../../components/layout/Skeleton';
import { Alert } from '../../components/ui/Alert';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { Select } from '../../components/ui/FormControls';
import { getHumanActionStatusMeta } from '../../lib/status';
import { formatDateTime, relativeTime } from '../../lib/formatters';
import { getActionTypeConfig } from '../../human-action/registry';

const PAGE_SIZE = 25;
const types = ['approval','leave_approval','finance_purchase_approval','supplier_selection','technician_action','information_request','identity_verification','onboarding_confirmation','policy_exception','customer_support_escalation'];

export function HumanActionsPage() {
  const [params, setParams] = useSearchParams();
  const [filtersOpen, setFiltersOpen] = useState(false);
  const { data: departments = [] } = useDepartments();
  const page = Math.max(1, Number(params.get('page') ?? 1));
  const query = useHumanActions({
    status: params.get('status') || undefined,
    action_type: params.get('type') || undefined,
    department_id: params.get('department') || undefined,
    assigned_role: params.get('role') || undefined,
    due_before: params.get('due') ? new Date(`${params.get('due')}T23:59:59`).toISOString() : undefined,
    request_id: params.get('request') || undefined,
    overdue_only: params.get('overdue') === 'true',
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });
  const actions = query.data ?? [];
  const pending = actions.filter(action => action.status === 'pending' && action.can_respond).length;
  const update = (key: string, value?: string) => { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); next.delete('page'); setParams(next); };
  const setPage = (value: number) => { const next = new URLSearchParams(params); if (value <= 1) next.delete('page'); else next.set('page', String(value)); setParams(next); };
  const controls = <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
    <Select label="Status" value={params.get('status') ?? ''} onChange={event => update('status', event.target.value || undefined)}><option value="">All statuses</option><option value="pending">Pending</option><option value="resolved">Completed</option><option value="cancelled">Cancelled</option></Select>
    <Select label="Action type" value={params.get('type') ?? ''} onChange={event => update('type', event.target.value || undefined)}><option value="">All action types</option>{types.map(type => <option key={type} value={type}>{getActionTypeConfig(type).label}</option>)}</Select>
    <Select label="Department" value={params.get('department') ?? ''} onChange={event => update('department', event.target.value || undefined)}><option value="">All departments</option>{departments.filter(item => item.is_active).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</Select>
    <Select label="Assigned role" value={params.get('role') ?? ''} onChange={event => update('role', event.target.value || undefined)}><option value="">All authorized roles</option><option value="company">Company account</option><option value="department_manager">Department manager</option></Select>
    <label className="grid gap-1.5 text-sm font-medium">Due on or before<input type="date" value={params.get('due') ?? ''} onChange={event => update('due', event.target.value || undefined)} className="h-10 rounded-lg border border-neutral-300 px-3 dark:border-neutral-700 dark:bg-neutral-950" /></label>
    <label className="grid gap-1.5 text-sm font-medium">Request ID<input value={params.get('request') ?? ''} onChange={event => update('request', event.target.value || undefined)} className="h-10 rounded-lg border border-neutral-300 px-3 dark:border-neutral-700 dark:bg-neutral-950" /></label>
    <label className="flex min-h-10 items-center gap-2 self-end text-sm"><input type="checkbox" checked={params.get('overdue') === 'true'} onChange={event => update('overdue', event.target.checked ? 'true' : undefined)} />Overdue only</label>
  </div>;

  return <PageContainer className="space-y-6">
    <PageHeader title="HumanActions" description="Review decisions and manual tasks assigned within your authorized scope."><Badge variant={pending ? 'warning' : 'neutral'}>{pending} requiring your action</Badge></PageHeader>
    <div className="hidden rounded-card border border-neutral-200 bg-white p-4 lg:block dark:border-neutral-800 dark:bg-neutral-900">{controls}</div>
    <Button variant="secondary" className="lg:hidden" onClick={() => setFiltersOpen(true)}><SlidersHorizontal size={16} className="mr-2" />Filters</Button>
    {query.isError && <Alert variant="error" title="Actions unavailable">The latest authorized actions could not be loaded.</Alert>}
    {query.isLoading ? <InboxSkeleton /> : actions.length ? <ActionResults actions={actions} /> : <Empty filtered={params.size > 0} />}
    {(page > 1 || actions.length === PAGE_SIZE) && <nav className="flex justify-between" aria-label="Action pages"><Button variant="secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button><span>Page {page}</span><Button variant="secondary" disabled={actions.length < PAGE_SIZE} onClick={() => setPage(page + 1)}>Next</Button></nav>}
    <Modal title="Filter actions" isOpen={filtersOpen} onClose={() => setFiltersOpen(false)}>{controls}<div className="mt-4 flex justify-end"><Button onClick={() => setFiltersOpen(false)}>Show actions</Button></div></Modal>
  </PageContainer>;
}

function ActionResults({ actions }: { actions: HumanActionSummary[] }) {
  const reduced = useReducedMotion();
  return <div className="grid gap-3">{actions.map((action, index) => { const status = getHumanActionStatusMeta(action.status); const overdue = action.status === 'pending' && action.due_date && new Date(action.due_date) < new Date(); return <motion.article key={action.id} initial={reduced ? false : { opacity: 0, y: 3 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(index, 4) * .03 }} className="rounded-card border border-neutral-200 bg-white p-4 shadow-xs dark:border-neutral-800 dark:bg-neutral-900"><div className="flex flex-col gap-4 sm:flex-row sm:items-start"><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><Badge category={overdue ? 'attention' : status.category}>{overdue ? 'Overdue' : status.label}</Badge><span className="text-xs font-semibold text-neutral-500">{getActionTypeConfig(action.action_type).label}</span></div><h2 className="mt-2 font-semibold">{action.title}</h2><div className="mt-2 flex flex-wrap gap-3 text-xs text-neutral-500"><span>Request {action.request_id.slice(0, 8).toUpperCase()}</span>{action.requesting_department && <span>{action.requesting_department}</span>}{action.due_date && <span className="inline-flex items-center gap-1"><Clock size={12} />Due {formatDateTime(action.due_date)}</span>}<span>Updated {relativeTime(action.updated_at)}</span></div></div><Link to={`/app/human-actions/${action.id}`} className="inline-flex min-h-10 items-center justify-center rounded-lg bg-primary-600 px-4 text-sm font-semibold text-white">{action.can_respond ? 'Review action' : 'View record'}<ArrowUpRight size={14} className="ml-2" /></Link></div></motion.article>; })}</div>;
}
function InboxSkeleton() { return <div role="status" aria-label="Loading actions" className="space-y-3">{Array.from({ length: 5 }, (_, index) => <Skeleton key={index} className="h-28 rounded-card" />)}</div>; }
function Empty({ filtered }: { filtered: boolean }) { return <div className="stagger-in rounded-card border border-dashed p-12 text-center"><span className="empty-float mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10"><Filter className="text-indigo-400/70" size={34} /></span><h2 className="mt-3 font-semibold">{filtered ? 'No actions match these filters' : 'No actions assigned'}</h2><p className="mt-2 text-sm text-neutral-500">{filtered ? 'Clear or adjust filters.' : 'Authorized HumanActions will appear here.'}</p></div>; }
