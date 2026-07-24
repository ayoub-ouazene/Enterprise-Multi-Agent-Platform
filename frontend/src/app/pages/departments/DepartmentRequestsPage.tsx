import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { PageContainer, PageHeader } from '../../../components/layout/PageContainer';
import { StatusBadge } from '../admin/components/StatusBadge';
import { ErrorState } from '../admin/components/ErrorState';
import { useDepartmentRequests } from '../../../api/hooks/useDepartments';
import { getDepartmentMeta, slugToDepartmentType } from '../../../lib/departments';
import { relativeTime } from '../../../lib/formatters';

const STATUS_OPTIONS = ['all', 'created', 'routing', 'processing', 'waiting_for_department', 'waiting_for_human_approval', 'waiting_for_human_action', 'under_review', 'completed', 'rejected', 'cancelled', 'failed'];

export function DepartmentRequestsPage() {
  const { deptSlug } = useParams<{ deptSlug: string }>();
  const navigate = useNavigate();
  const deptType = deptSlug ? slugToDepartmentType(deptSlug) : undefined;
  const meta = deptType ? getDepartmentMeta(deptType) : undefined;

  const [status, setStatus] = useState('all');
  const [q, setQ] = useState('');

  const { data: requests, isLoading, error } = useDepartmentRequests(deptType ?? '', {
    status: status === 'all' ? undefined : status,
    limit: 50,
  });

  if (!deptType || !meta) {
    return (
      <PageContainer>
        <ErrorState message="The department does not exist." />
      </PageContainer>
    );
  }

  const filtered = requests?.filter((r) =>
    q.trim() ? r.title.toLowerCase().includes(q.toLowerCase()) || r.request_type.toLowerCase().includes(q.toLowerCase()) : true
  );

  return (
    <PageContainer>
      <PageHeader title="Requests" description={`${meta.label} request list`} />

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

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-md bg-neutral-100 dark:bg-neutral-800" />
          ))}
        </div>
      )}

      {error && <ErrorState message="Failed to load requests. Please try again." />}

      {!isLoading && !error && (
        <div className="space-y-2">
          {filtered && filtered.length > 0 ? (
            filtered.map((req) => (
              <button
                key={req.id}
                onClick={() => navigate(`/app/requests/${req.id}`)}
                className="flex w-full items-center justify-between rounded-md border border-neutral-200 bg-white px-4 py-3 text-left transition-colors hover:border-neutral-300 dark:border-neutral-800 dark:bg-neutral-800 dark:hover:border-neutral-700"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-100">{req.title}</p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400">{req.request_type} &middot; {relativeTime(req.created_at)}</p>
                </div>
                <StatusBadge
                  status={req.status === 'completed' ? 'success' : req.status === 'failed' || req.status === 'rejected' ? 'error' : 'info'}
                >
                  {req.status.replace(/_/g, ' ')}
                </StatusBadge>
              </button>
            ))
          ) : (
            <p className="text-sm text-neutral-500 dark:text-neutral-400">No requests found.</p>
          )}
        </div>
      )}
    </PageContainer>
  );
}
