import { useState } from 'react';
import { CheckCircle, Clock, XCircle, Lightbulb } from 'lucide-react';
import { PageContainer, PageHeader } from '../../../components/layout/PageContainer';
import { Skeleton } from '../../../components/layout/Skeleton';
import { EmptyState } from '../../../components/ui/EmptyState';
import { Button } from '../../../components/ui/Button';
import { useCapabilityGaps, useUpdateCapabilityGapStatus } from '../../../api/hooks/useFailures';
import { CapabilityGapStatus } from '../../../api/types';
import { ErrorState } from './components/ErrorState';
import { relativeTime } from '../../../lib/formatters';

export function CapabilityGapsPage() {
  const [statusFilter, setStatusFilter] = useState<CapabilityGapStatus | ''>('');
  const filters = statusFilter ? { status: statusFilter } : {};
  const { data: gaps, isLoading, error } = useCapabilityGaps(filters);
  const updateStatus = useUpdateCapabilityGapStatus();

  return (
    <PageContainer>
      <PageHeader title="Capability Gaps" description="Track unsupported or unplanned operations" />

      <div className="mb-4 flex flex-wrap gap-3">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as CapabilityGapStatus | '')}
          className="h-9 rounded-md border border-neutral-300 bg-white px-3 text-sm dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
        >
          <option value="">All statuses</option>
          {Object.values(CapabilityGapStatus).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {error && <ErrorState message="Failed to load capability gaps." />}

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : !gaps || gaps.length === 0 ? (
        <EmptyState title="No capability gaps" description="The platform has not encountered unsupported operations." />
      ) : (
        <div className="space-y-3">
          {gaps.map((gap) => (
            <div key={gap.id} className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-800">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${gap.status === CapabilityGapStatus.RESOLVED ? 'bg-success-100 text-success-600' : gap.status === CapabilityGapStatus.REJECTED ? 'bg-neutral-100 text-neutral-600' : 'bg-warning-100 text-warning-600'}`}>
                    {gap.status === CapabilityGapStatus.RESOLVED ? <CheckCircle size={14} /> : gap.status === CapabilityGapStatus.REJECTED ? <XCircle size={14} /> : <Lightbulb size={14} />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{gap.requested_operation}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
                      <GapStatusChip status={gap.status} />
                      <span className="inline-flex items-center gap-1">
                        <Clock size={12} />
                        {relativeTime(gap.last_seen_at)}
                      </span>
                      <span>Occurrences: {gap.occurrence_count}</span>
                    </div>
                  </div>
                </div>

                {gap.status !== CapabilityGapStatus.RESOLVED && gap.status !== CapabilityGapStatus.REJECTED && (
                  <div className="flex shrink-0 gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      className="text-xs"
                      onClick={() =>
                        updateStatus.mutate({
                          gapId: gap.id,
                          payload: { status: CapabilityGapStatus.ACKNOWLEDGED },
                        })
                      }
                      isLoading={updateStatus.isPending && updateStatus.variables?.payload.status === CapabilityGapStatus.ACKNOWLEDGED}
                    >
                      Acknowledge
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      className="text-xs"
                      onClick={() =>
                        updateStatus.mutate({
                          gapId: gap.id,
                          payload: { status: CapabilityGapStatus.RESOLVED, resolution_notes: 'Resolved' },
                        })
                      }
                      isLoading={updateStatus.isPending && updateStatus.variables?.payload.status === CapabilityGapStatus.RESOLVED}
                    >
                      Resolve
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </PageContainer>
  );
}

function GapStatusChip({ status }: { status: CapabilityGapStatus }) {
  const map: Record<CapabilityGapStatus, string> = {
    open: 'bg-danger-50 text-danger-700 dark:bg-danger-900/20 dark:text-danger-300',
    acknowledged: 'bg-warning-50 text-warning-700 dark:bg-warning-900/20 dark:text-warning-300',
    planned: 'bg-info-50 text-info-700 dark:bg-info-900/20 dark:text-info-300',
    resolved: 'bg-success-50 text-success-700 dark:bg-success-900/20 dark:text-success-300',
    rejected: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-400',
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${map[status]}`}>
      {status}
    </span>
  );
}
