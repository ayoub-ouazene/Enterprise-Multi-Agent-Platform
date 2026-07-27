import { useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AlertTriangle, CalendarClock, Hand } from 'lucide-react';
import { PageContainer, PageHeader } from '../../../components/layout/PageContainer';
import { StatusBadge } from '../admin/components/StatusBadge';
import { ErrorState } from '../admin/components/ErrorState';
import { EmptyState } from '../../../components/ui/EmptyState';
import { Tabs } from '../../../components/ui/Tabs';
import { useDepartmentActions } from '../../../api/hooks/useDepartments';
import { getDepartmentMeta, slugToDepartmentType } from '../../../lib/departments';
import { relativeTime } from '../../../lib/formatters';

const STATUS_OPTIONS = [
  { value: 'pending', label: 'Pending' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'all', label: 'All' },
];

function dueUrgency(dueDate: string | null): 'critical' | 'warning' | 'normal' {
  if (!dueDate) return 'normal';
  const diff = new Date(dueDate).getTime() - Date.now();
  const hours = diff / (1000 * 60 * 60);
  if (hours < 0) return 'critical';
  if (hours < 24) return 'warning';
  return 'normal';
}

export function DepartmentActionsPage() {
  const { deptSlug } = useParams<{ deptSlug: string }>();
  const navigate = useNavigate();
  const deptType = deptSlug ? slugToDepartmentType(deptSlug) : undefined;
  const meta = deptType ? getDepartmentMeta(deptType) : undefined;

  const [status, setStatus] = useState('pending');
  const [typeFilter, setTypeFilter] = useState<string>('all');

  const { data: actions, isLoading, error } = useDepartmentActions(deptType ?? '', {
    status: status === 'all' ? undefined : status,
    limit: 50,
  });

  const actionTypes = useMemo(() => {
    const types = new Set<string>();
    (actions ?? []).forEach((a) => types.add(a.action_type));
    return Array.from(types).sort();
  }, [actions]);

  const typeItems = useMemo(
    () => [
      { value: 'all', label: 'All types', count: undefined },
      ...actionTypes.map((t) => ({
        value: t,
        label: t.replace(/_/g, ' '),
        count: typeFilter === 'all' ? (actions ?? []).filter((a) => a.action_type === t).length : undefined,
      })),
    ],
    [actionTypes, typeFilter, actions],
  );

  const filtered = useMemo(
    () =>
      (actions ?? []).filter(
        (a) => typeFilter === 'all' || a.action_type === typeFilter,
      ),
    [actions, typeFilter],
  );

  if (!deptType || !meta) {
    return (
      <PageContainer>
        <ErrorState message="The department does not exist." />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader title="Human Actions" description={`Actions assigned to ${meta.label}`} />

      <Tabs items={STATUS_OPTIONS} value={status} onChange={setStatus} label="Action status filter" />
      <div className="mt-2">
        <Tabs items={typeItems} value={typeFilter} onChange={setTypeFilter} label="Action type filter" />
      </div>

      {isLoading && (
        <div className="mt-4 space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-md bg-neutral-100 dark:bg-neutral-800" />
          ))}
        </div>
      )}

      {error && <ErrorState message="Failed to load actions. Please try again." />}

      {!isLoading && !error && (
        <div className="mt-4 space-y-2">
          {filtered.length > 0 ? (
            filtered.map((action) => {
              const urgency = dueUrgency(action.due_date);
              return (
                <button
                  key={action.id}
                  onClick={() => navigate(`/app/human-actions/${action.id}`)}
                  className="flex w-full min-h-[4.5rem] items-center justify-between rounded-xl border border-neutral-200 bg-white px-4 py-3 text-left transition-colors hover:border-primary-300 dark:border-neutral-800 dark:bg-neutral-900"
                >
                  <div className="flex min-w-0 items-start gap-3">
                    <Hand size={16} className="mt-0.5 shrink-0 text-warning-500" />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-100">{action.title}</p>
                      <div className="mt-1 flex flex-wrap items-center gap-2">
                        <span className="text-xs text-neutral-500">{action.action_type.replace(/_/g, ' ')}</span>
                        {action.due_date && (
                          <span className={`inline-flex items-center gap-1 text-[11px] font-medium ${urgency === 'critical' ? 'text-error-600 dark:text-error-400' : urgency === 'warning' ? 'text-warning-600 dark:text-warning-400' : 'text-neutral-500'}`}>
                            {urgency === 'critical' ? <AlertTriangle size={11} /> : <CalendarClock size={11} />}
                            Due {relativeTime(action.due_date)}
                          </span>
                        )}
                        {action.request_title && (
                          <span className="text-[11px] text-neutral-400">· {action.request_title}</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <StatusBadge status={status === 'completed' ? 'success' : status === 'cancelled' ? 'neutral' : urgency === 'critical' ? 'error' : urgency === 'warning' ? 'warning' : 'warning'}>
                    {action.status.replace(/_/g, ' ')}
                  </StatusBadge>
                </button>
              );
            })
          ) : (
            <EmptyState title={`No ${meta.shortLabel} actions matching your filters`} description="Actions appear when the workflow requires human response." />
          )}
        </div>
      )}
    </PageContainer>
  );
}
