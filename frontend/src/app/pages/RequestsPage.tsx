import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Skeleton } from '../../components/layout/Skeleton';
import { RequestSummaryCard } from '../../components/request/RequestSummaryCard';
import { Button } from '../../components/ui/Button';
import { Alert } from '../../components/ui/Alert';
import { EmptyState } from '../../components/ui/EmptyState';
import { useRequests } from '../../api/hooks/useRequests';
import { RequestStatus } from '../../api/types';

const statusOptions: { label: string; value: string }[] = [
  { label: 'All', value: '' },
  { label: 'Active', value: 'active' },
  { label: 'Completed', value: RequestStatus.COMPLETED },
  { label: 'Failed', value: 'failed,rejected' },
  { label: 'Pending Action', value: RequestStatus.PENDING_ACTION },
  { label: 'Pending Approval', value: RequestStatus.PENDING_APPROVAL },
];

export function RequestsPage() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');

  const filters: Record<string, string | undefined> = { status: undefined, limit: '50' };
  if (statusFilter === 'active') {
    filters.status = undefined; // Active filter is client-side
  } else if (statusFilter) {
    filters.status = statusFilter;
  }

  const { data: requests, isLoading, error, refetch } = useRequests(filters);

  const activeStatuses = [RequestStatus.DRAFT, RequestStatus.SUBMITTED, RequestStatus.IN_PROGRESS, RequestStatus.PENDING_APPROVAL, RequestStatus.PENDING_ACTION];

  let filtered = requests ?? [];
  if (statusFilter === 'active') {
    filtered = filtered.filter((r) => activeStatuses.includes(r.status as RequestStatus));
  }
  if (search.trim()) {
    const q = search.toLowerCase();
    filtered = filtered.filter((r) =>
      r.title.toLowerCase().includes(q) ||
      r.request_type.toLowerCase().includes(q) ||
      r.summary.toLowerCase().includes(q)
    );
  }

  return (
    <PageContainer>
      <PageHeader title="Requests" description="Manage and track all requests">
        <Button onClick={() => navigate('/app/requests/new')}>
          <Plus size={16} className="mr-1.5" aria-hidden="true" />
          New Request
        </Button>
      </PageHeader>

      {/* Controls */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative max-w-xs">
          <Search size={16} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-400" aria-hidden="true" />
          <input
            type="text"
            placeholder="Search requests..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 w-full rounded-md border border-neutral-300 bg-white py-1.5 pl-9 pr-3 text-sm placeholder:text-neutral-400 focus-visible:border-primary-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100 dark:placeholder:text-neutral-500"
          />
        </div>
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter requests by status">
          {statusOptions.map((opt) => {
            const active = statusFilter === opt.value;
            return (
              <button
                key={opt.value}
                role="tab"
                aria-selected={active}
                onClick={() => setStatusFilter(opt.value)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  active
                    ? 'bg-neutral-900 text-white dark:bg-primary-600 dark:text-white'
                    : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-400 dark:hover:bg-neutral-700'
                }`}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {error && (
        <Alert variant="error" title="Error loading requests">
          <div className="flex items-center justify-between">
            <span>{error instanceof Error ? error.message : 'Please try again.'}</span>
            <Button size="sm" variant="secondary" onClick={() => refetch()}>Retry</Button>
          </div>
        </Alert>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-lg border border-neutral-200 bg-white p-4 shadow-xs dark:border-neutral-800 dark:bg-neutral-800">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <Skeleton variant="text" className="w-40" />
                  <Skeleton variant="text" className="mt-2 w-3/4" />
                </div>
                <Skeleton variant="rect" className="h-5 w-16 rounded-full" />
              </div>
            </div>
          ))}
        </div>
      ) : filtered.length > 0 ? (
        <div className="space-y-3">
          {filtered.map((req) => (
            <RequestSummaryCard
              key={req.id}
              request={req}
              onClick={() => navigate(`/app/requests/${req.id}`)}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-neutral-200 bg-white p-8 shadow-xs dark:border-neutral-800 dark:bg-neutral-800">
          <EmptyState
            title={search ? 'No matching requests' : 'No requests yet'}
            description={search ? 'Try a different search term.' : 'Create your first request to get started.'}
            action={!search ? (
              <Button onClick={() => navigate('/app/requests/new')}>
                <Plus size={16} className="mr-1.5" aria-hidden="true" />
                New Request
              </Button>
            ) : undefined}
          />
        </div>
      )}
    </PageContainer>
  );
}
