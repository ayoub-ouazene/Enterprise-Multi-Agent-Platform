import {
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  ClipboardList,
  Hand,
  RefreshCw,
  Settings,
} from 'lucide-react';
import { useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  useDepartmentActions,
  useDepartmentActivity,
  useDepartmentOperationalRecords,
  useDepartmentReadiness,
  useDepartmentRequests,
  useDepartmentStats,
} from '../../../api/hooks/useDepartments';
import { useAuthContext } from '../../../auth/hooks/useAuthContext';
import { ActorType, RequestStatus } from '../../../api/types';
import type { BusinessRequestSummary } from '../../../api/types';
import { getDepartmentMeta, slugToDepartmentType } from '../../../lib/departments';
import { relativeTime } from '../../../lib/formatters';
import { PageContainer, PageHeader, Section } from '../../../components/layout/PageContainer';
import { Alert } from '../../../components/ui/Alert';
import { Button } from '../../../components/ui/Button';
import { EmptyState } from '../../../components/ui/EmptyState';
import { StatCard } from '../admin/components/StatCard';
import { StatusBadge } from '../admin/components/StatusBadge';
import { TableSkeleton } from '../admin/components/TableSkeleton';
import { OperationalRecordCard } from './DepartmentOperationsPage';

export function DepartmentOverviewPage() {
  const { deptSlug } = useParams<{ deptSlug: string }>();
  const navigate = useNavigate();
  const { user } = useAuthContext();
  const departmentType = deptSlug ? slugToDepartmentType(deptSlug) : undefined;
  const meta = departmentType ? getDepartmentMeta(departmentType) : undefined;
  const stats = useDepartmentStats(departmentType ?? '');
  const requests = useDepartmentRequests(departmentType ?? '', { limit: 8 });
  const actions = useDepartmentActions(departmentType ?? '', { status: 'pending', limit: 5 });
  const readiness = useDepartmentReadiness(departmentType ?? '');
  const records = useDepartmentOperationalRecords(departmentType ?? '', { limit: 8 });
  const activity = useDepartmentActivity(departmentType ?? '', 15);

  const attentionRequests = requests.data?.filter((request) => request.attention_required) ?? [];
  const missingReadiness = readiness.data?.items.filter((item) => !item.ready) ?? [];
  const collaborations = activity.data?.filter((event) => event.event_type.includes('collaboration')).slice(0, 4) ?? [];
  const canManage = user?.actor_type === ActorType.COMPANY || user?.actor_type === ActorType.DEPARTMENT_MANAGER;
  const activeSorted = useMemo(() => sortedByDepartmentPriority(requests.data ?? [], departmentType ?? ''), [requests.data, departmentType]);

  if (!departmentType || !meta) return <PageContainer><Alert variant="error">Unknown department workspace.</Alert></PageContainer>;

  return (
    <PageContainer>
      <PageHeader title={meta.label} description={meta.description}>
        <Button onClick={() => navigate('/app/requests/new')}>Create request</Button>
      </PageHeader>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Active work" value={stats.data?.active_requests ?? '—'} icon={<ClipboardList size={18} />} color="blue" />
        <StatCard label="Pending actions" value={stats.data?.pending_human_actions ?? '—'} icon={<Hand size={18} />} color={stats.data?.pending_human_actions ? 'amber' : 'emerald'} />
        <StatCard label="Collaborations" value={stats.data?.collaborations_ongoing ?? '—'} icon={<RefreshCw size={18} />} color="purple" />
        <StatCard label="Completed today" value={stats.data?.completed_today ?? '—'} icon={<CheckCircle size={18} />} color="emerald" />
      </div>

      {stats.isError && <Alert variant="error">Workload metrics are unavailable. Operational records and actions may still be used.</Alert>}

      <Section title="Attention required">
        <div className="grid gap-3 lg:grid-cols-2">
          {missingReadiness.map((item) => (
            <AttentionItem key={item.name} title={item.name} detail={item.detail ?? 'Department setup requires attention.'} onOpen={() => navigate('/app/admin/policies')} />
          ))}
          {attentionRequests.slice(0, 4).map((request) => (
            <AttentionItem key={request.id} title={request.title} detail={request.current_state_summary} onOpen={() => navigate(`/app/requests/${request.id}`)} />
          ))}
          {actions.data?.slice(0, 3).map((action) => (
            <AttentionItem key={action.id} title={action.title} detail={`HumanAction · ${action.action_type.replaceAll('_', ' ')}`} onOpen={() => navigate(`/app/human-actions/${action.id}`)} />
          ))}
        </div>
        {!readiness.isLoading && !requests.isLoading && !actions.isLoading && missingReadiness.length + attentionRequests.length + (actions.data?.length ?? 0) === 0 && (
          <Alert variant="success">No immediate department attention is reported.</Alert>
        )}
      </Section>

      <Section title="Active work">
        {requests.isLoading && <TableSkeleton rows={4} />}
        {requests.isError && <Alert variant="error">Request workload could not be loaded.</Alert>}
        <div className="grid gap-2">
          {activeSorted.slice(0, 6).map((request) => {
            const relationship = request.owner_department?.department_type === departmentType
              ? 'Owned by this department'
              : request.active_department?.department_type === departmentType
                ? `Assisting ${request.owner_department?.name ?? 'another department'}`
                : 'Waiting outside this department';
            return (
              <button key={request.id} onClick={() => navigate(`/app/requests/${request.id}`)} className="flex min-h-16 w-full items-center justify-between gap-3 rounded-xl border border-neutral-200 bg-white px-4 py-3 text-left transition-colors hover:border-primary-300 dark:border-neutral-800 dark:bg-neutral-900">
                <span className="min-w-0"><strong className="block truncate text-sm">{request.title}</strong><span className="mt-1 block text-xs text-neutral-500">{relationship} · {relativeTime(request.updated_at)}</span></span>
                <StatusBadge status={request.status === RequestStatus.FAILED ? 'error' : request.attention_required ? 'warning' : 'info'}>{request.status.replaceAll('_', ' ')}</StatusBadge>
              </button>
            );
          })}
        </div>
        {!requests.isLoading && requests.data?.length === 0 && <EmptyState title={`No active ${meta.shortLabel} requests`} description="Owned and active collaboration requests will appear here." />}
        <Button variant="ghost" className="mt-3" onClick={() => navigate(`/app/departments/${deptSlug}/requests`)}>View all requests <ArrowRight size={14} className="ml-2" /></Button>
      </Section>

      <Section title="Operational summary">
        {records.isLoading && <TableSkeleton rows={3} />}
        {records.isError && <Alert variant="error">Operational extension records are unavailable; request tracking remains available.</Alert>}
        <div className="grid gap-4 xl:grid-cols-2">
          {records.data?.slice(0, 4).map((record) => <OperationalRecordCard key={`${record.record_type}-${record.id}`} record={record} />)}
        </div>
        {!records.isLoading && records.data?.length === 0 && <EmptyState title={`No ${meta.shortLabel} operational records`} description="The workspace does not fabricate records before a supported workflow creates them." />}
        <Button variant="ghost" className="mt-3" onClick={() => navigate(`/app/departments/${deptSlug}/operations`)}>Open operations <ArrowRight size={14} className="ml-2" /></Button>
      </Section>

      <div className="grid gap-5 xl:grid-cols-2">
        <Section title="Collaboration activity">
          {collaborations.length === 0 ? <p className="text-sm text-neutral-500">No recent safe collaboration events.</p> : collaborations.map((event) => (
            <button key={event.id} onClick={() => navigate(`/app/requests/${event.request_id}`)} className="mb-2 block w-full rounded-lg border border-neutral-200 p-3 text-left dark:border-neutral-800">
              <strong className="text-sm">{event.title}</strong>
              <p className="mt-1 text-sm text-neutral-500">{event.message}</p>
              <span className="mt-1 block text-xs text-neutral-400">{relativeTime(event.created_at)}</span>
            </button>
          ))}
        </Section>
        <Section title="Quick actions">
          <div className="grid gap-2">
            <Button variant="secondary" onClick={() => navigate(`/app/departments/${deptSlug}/actions`)}>Open relevant HumanActions</Button>
            <Button variant="secondary" onClick={() => navigate(`/app/departments/${deptSlug}/activity`)}>Review safe activity</Button>
            {canManage && meta.resourceLinks.map((link) => <Button key={link.href} variant="ghost" onClick={() => navigate(link.href)}><Settings size={14} className="mr-2" />{link.label}</Button>)}
          </div>
        </Section>
      </div>
    </PageContainer>
  );
}

export function sortedByDepartmentPriority(list: BusinessRequestSummary[], departmentType: string) {
  const priorityWeights: Record<string, number> = { urgent: 0, high: 1, normal: 2, low: 3 };
  const weights: Record<string, number> = {
    [RequestStatus.FAILED]: 0,
    [RequestStatus.WAITING_FOR_HUMAN_ACTION]: 1,
    [RequestStatus.WAITING_FOR_HUMAN_APPROVAL]: 2,
    [RequestStatus.WAITING_FOR_DEPARTMENT]: 3,
    [RequestStatus.UNDER_REVIEW]: 4,
    [RequestStatus.PROCESSING]: 5,
    [RequestStatus.ROUTING]: 6,
    [RequestStatus.CREATED]: 7,
    remaining: 8,
  };
  const relationWeight = (item: BusinessRequestSummary) => {
    if (item.owner_department?.department_type === departmentType) return 0;
    if (item.active_department?.department_type === departmentType) return 1;
    return 2;
  };
  return [...list].sort((a, b) => {
    const pa = a.attention_required ? -1 : 1;
    const pb = b.attention_required ? -1 : 1;
    if (pa !== pb) return pa - pb;
    const ra = relationWeight(a);
    const rb = relationWeight(b);
    if (ra !== rb) return ra - rb;
    const wa = weights[a.status] ?? weights.remaining;
    const wb = weights[b.status] ?? weights.remaining;
    if (wa !== wb) return wa - wb;
    const pa2 = priorityWeights[a.priority] ?? 99;
    const pb2 = priorityWeights[b.priority] ?? 99;
    return pa2 - pb2;
  });
}

function AttentionItem({ title, detail, onOpen }: { title: string; detail: string; onOpen: () => void }) {
  return (
    <button onClick={onOpen} className="flex min-h-16 items-center gap-3 rounded-xl border border-warning-200 bg-warning-50/50 px-4 py-3 text-left dark:border-warning-900/60 dark:bg-warning-950/20">
      <AlertTriangle size={17} className="shrink-0 text-warning-600" />
      <span className="min-w-0 flex-1"><strong className="block truncate text-sm">{title}</strong><span className="mt-0.5 block line-clamp-2 text-xs text-neutral-500">{detail}</span></span>
      <ArrowRight size={14} className="shrink-0 text-neutral-400" />
    </button>
  );
}
