import { useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AlertTriangle, CheckCircle, RefreshCw, Search, Users } from 'lucide-react';
import { PageContainer, PageHeader } from '../../../components/layout/PageContainer';
import { StatusBadge } from '../admin/components/StatusBadge';
import { ErrorState } from '../admin/components/ErrorState';
import { EmptyState } from '../../../components/ui/EmptyState';
import { Tabs } from '../../../components/ui/Tabs';
import { useDepartmentRequests } from '../../../api/hooks/useDepartments';
import { getDepartmentMeta, slugToDepartmentType } from '../../../lib/departments';
import { relativeTime } from '../../../lib/formatters';
import { RequestPriority, RequestStatus } from '../../../api/types';
import type { BusinessRequestSummary } from '../../../api/types';

const STATUS_OPTIONS = ['all', 'created', 'routing', 'processing', 'waiting_for_department', 'waiting_for_human_approval', 'waiting_for_human_action', 'under_review', 'completed', 'rejected', 'cancelled', 'failed'];

const RELATION_FILTER_ITEMS = [
  { value: 'all', label: 'All relation' },
  { value: 'owned', label: 'Owned' },
  { value: 'collaborating', label: 'Collaborating' },
];

const ATTENTION_FILTER_ITEMS = [
  { value: 'all', label: 'All attention' },
  { value: 'attention', label: 'Needs attention' },
  { value: 'normal', label: 'Normal' },
];

function requestRelation(request: Pick<BusinessRequestSummary, 'owner_department_id' | 'active_department_id'>, departmentId: string | null) {
  if (!departmentId) return 'other' as const;
  if (request.owner_department_id === departmentId) return 'owned' as const;
  if (request.active_department_id === departmentId) return 'collaborating' as const;
  return 'other' as const;
}

function relationBadgeConfig(rel: string) {
  if (rel === 'owned') return { icon: <CheckCircle size={12} className="mr-1" />, label: 'Owned' };
  if (rel === 'collaborating') return { icon: <RefreshCw size={12} className="mr-1" />, label: 'Collaborating' };
  return { icon: <Users size={12} className="mr-1" />, label: 'External' };
}

function priorityConfig(priority: string) {
  if (priority === RequestPriority.URGENT) return 'error' as const;
  if (priority === RequestPriority.HIGH) return 'warning' as const;
  if (priority === RequestPriority.NORMAL) return 'info' as const;
  return 'neutral' as const;
}

export function DepartmentRequestsPage() {
  const { deptSlug } = useParams<{ deptSlug: string }>();
  const navigate = useNavigate();
  const deptType = deptSlug ? slugToDepartmentType(deptSlug) : undefined;
  const meta = deptType ? getDepartmentMeta(deptType) : undefined;

  const [status, setStatus] = useState('all');
  const [q, setQ] = useState('');
  const [relation, setRelation] = useState('all');
  const [attention, setAttention] = useState('all');

  const { data: requests, isLoading, error } = useDepartmentRequests(deptType ?? '', {
    status: status === 'all' ? undefined : status,
    limit: 100,
  });

  const departmentId = useMemo(() => {
    if (!requests || requests.length === 0) return null;
    const owned = requests.find((r) => r.owner_department?.department_type === deptType);
    return owned?.owner_department_id ?? requests[0]?.owner_department_id ?? null;
  }, [requests, deptType]);

  const relations = useMemo(() => {
    const map = new Map<string, 'owned' | 'collaborating' | 'other'>();
    for (const req of requests ?? []) {
      map.set(req.id, requestRelation(req, departmentId));
    }
    return map;
  }, [requests, departmentId]);

  const associationCounts = useMemo(() => ({
    owned: (requests ?? []).filter((r) => relations.get(r.id) === 'owned').length,
    collaborating: (requests ?? []).filter((r) => relations.get(r.id) === 'collaborating').length,
  }), [requests, relations]);

  const filtered = useMemo(() => {
    const list = requests ?? [];
    return list.filter((r) => {
      const matchText = q.trim() ? r.title.toLowerCase().includes(q.toLowerCase()) || r.request_type.toLowerCase().includes(q.toLowerCase()) : true;
      const rel = relations.get(r.id) ?? 'other';
      const matchRel = relation === 'all' || rel === relation;
      const matchAttention = attention === 'all' || (attention === 'attention' && r.attention_required) || (attention === 'normal' && !r.attention_required);
      return matchText && matchRel && matchAttention;
    });
  }, [requests, q, relation, attention, relations]);

  if (!deptType || !meta) {
    return (
      <PageContainer>
        <ErrorState message="The department does not exist." />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader title="Requests" description={`${meta.label} owned and collaborating requests`} />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-400" />
          <input
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search by title or type..."
            className="w-full rounded-md border border-neutral-300 bg-white py-2 pl-8 pr-3 text-sm dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100"
          />
        </div>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100"
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s === 'all' ? 'All statuses' : s.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
      </div>

      <Tabs items={RELATION_FILTER_ITEMS.map((item) => ({ value: item.value, label: item.label, count: relation === 'all' ? (item.value === 'owned' ? associationCounts.owned : item.value === 'collaborating' ? associationCounts.collaborating : undefined) : undefined }))} value={relation} onChange={setRelation} label="Request relation filter" />
      <div className="mt-2">
        <Tabs items={ATTENTION_FILTER_ITEMS} value={attention} onChange={setAttention} label="Attention filter" />
      </div>

      {isLoading && (
        <div className="mt-4 space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-md bg-neutral-100 dark:bg-neutral-800" />
          ))}
        </div>
      )}

      {error && <ErrorState message="Failed to load requests. Please try again." />}

      {!isLoading && !error && (
        <div className="mt-4 space-y-2">
          {filtered.length > 0 ? (
            filtered.map((req) => {
              const rel = relations.get(req.id) ?? 'other';
              const { icon, label: relationLabel } = relationBadgeConfig(rel);
              return (
                <button
                  key={req.id}
                  onClick={() => navigate(`/app/requests/${req.id}`)}
                  className="flex w-full min-h-[4.5rem] items-center justify-between rounded-xl border border-neutral-200 bg-white px-4 py-3 text-left transition-colors hover:border-primary-300 dark:border-neutral-800 dark:bg-neutral-900"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-100">{req.title}</p>
                      {req.attention_required && <span title="Needs attention"><AlertTriangle size={13} className="shrink-0 text-warning-500" /></span>}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <span className="inline-flex items-center text-[11px] font-medium text-neutral-400">{icon}{relationLabel}</span>
                      <span className="text-xs text-neutral-500">{req.request_type} &middot; {relativeTime(req.updated_at)}</span>
                      <StatusBadge status={priorityConfig(req.priority)}>{req.priority}</StatusBadge>
                    </div>
                  </div>
                  <StatusBadge
                    status={req.status === RequestStatus.COMPLETED ? 'success' : req.status === RequestStatus.FAILED || req.status === RequestStatus.REJECTED ? 'error' : req.attention_required ? 'warning' : 'info'}
                  >
                    {req.status.replace(/_/g, ' ')}
                  </StatusBadge>
                </button>
              );
            })
          ) : (
            <EmptyState title={`No ${meta.shortLabel} requests matching your filters`} description="Try adjusting the search term or relation filter." />
          )}
        </div>
      )}
    </PageContainer>
  );
}
