import { useState } from 'react';
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { PageContainer, PageHeader } from '../../../components/layout/PageContainer';
import { Skeleton } from '../../../components/layout/Skeleton';
import { EmptyState } from '../../../components/ui/EmptyState';
import { useFailures } from '../../../api/hooks/useFailures';
import { FailureType, FailureSource } from '../../../api/types';
import { ErrorState } from './components/ErrorState';
import { relativeTime } from '../../../lib/formatters';

export function FailuresPage() {
  const [typeFilter, setTypeFilter] = useState<FailureType | ''>('');
  const [sourceFilter, setSourceFilter] = useState<FailureSource | ''>('');
  const [resolvedFilter, setResolvedFilter] = useState<string>('');

  const filters = {
    ...(typeFilter ? { failure_type: typeFilter } : {}),
    ...(sourceFilter ? { failure_source: sourceFilter } : {}),
    ...(resolvedFilter ? { resolved: resolvedFilter === 'resolved' } : {}),
    limit: 50,
  };

  const { data: failures, isLoading, error } = useFailures(filters);

  return (
    <PageContainer>
      <PageHeader title="Failure Logs" description="View platform failures and errors" />

      <div className="mb-4 flex flex-wrap gap-3">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as FailureType | '')}
          className="h-9 rounded-md border border-neutral-300 bg-white px-3 text-sm dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
        >
          <option value="">All types</option>
          {Object.values(FailureType).map((t) => (
            <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
          ))}
        </select>
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value as FailureSource | '')}
          className="h-9 rounded-md border border-neutral-300 bg-white px-3 text-sm dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
        >
          <option value="">All sources</option>
          {Object.values(FailureSource).map((s) => (
            <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
          ))}
        </select>
        <select
          value={resolvedFilter}
          onChange={(e) => setResolvedFilter(e.target.value)}
          className="h-9 rounded-md border border-neutral-300 bg-white px-3 text-sm dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
        >
          <option value="">All statuses</option>
          <option value="resolved">Resolved</option>
          <option value="open">Unresolved</option>
        </select>
      </div>

      {error && <ErrorState message="Failed to load failure logs." />}

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : !failures || failures.length === 0 ? (
        <EmptyState title="No failures" description="The platform is operating without recorded failures." />
      ) : (
        <div className="space-y-3">
          {failures.map((f) => (
            <div key={f.id} className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-800">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${f.resolved ? 'bg-success-100 text-success-600' : f.is_terminal ? 'bg-danger-100 text-danger-600' : 'bg-warning-100 text-warning-600'}`}>
                    {f.resolved ? <CheckCircle size={14} /> : f.is_terminal ? <XCircle size={14} /> : <AlertTriangle size={14} />}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{f.failed_operation}</p>
                      {f.error_code && (
                        <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400">{f.error_code}</span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{f.safe_message}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <span className="inline-flex items-center rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-700 dark:bg-neutral-700 dark:text-neutral-300">{f.failure_type.replace(/_/g, ' ')}</span>
                      <span className="inline-flex items-center rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-700 dark:bg-neutral-700 dark:text-neutral-300">{f.failure_source.replace(/_/g, ' ')}</span>
                      {f.alternative_attempted && <span className="text-xs text-info-600 dark:text-info-400">alternative tried</span>}
                    </div>
                  </div>
                </div>
                <span className="shrink-0 text-xs text-neutral-400 dark:text-neutral-500">{relativeTime(f.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </PageContainer>
  );
}
