import { AlertCircle, CheckCircle2 } from 'lucide-react';
import { useAdminPolicyReadiness } from '../../../api/hooks/useAdmin';
import { SectionCard } from './components/SectionCard';
import { ErrorState } from './components/ErrorState';
import { TableSkeleton } from './components/TableSkeleton';
import { StatusBadge } from './components/StatusBadge';

export function PoliciesPage() {
  const { data, isLoading, error } = useAdminPolicyReadiness();

  if (isLoading) return <TableSkeleton rows={4} />;
  if (error) return <ErrorState message="Failed to load policy readiness." />;

  const coverage = data?.department_coverage ?? {};
  const allReady = data?.ready ?? false;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <SectionCard title="Policy Readiness">
        <div className="flex items-center gap-3">
          <div className={`flex h-10 w-10 items-center justify-center rounded-full ${allReady ? 'bg-emerald-100 text-emerald-600' : 'bg-amber-100 text-amber-600'} dark:${allReady ? 'bg-emerald-900/30' : 'bg-amber-900/30'}`}>
            {allReady ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
          </div>
          <div>
            <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
              {allReady ? 'Policies Ready' : 'Policies Incomplete'}
            </p>
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              {data?.ingested_active_policies ?? 0} ingested policies across {Object.keys(coverage).length} departments
            </p>
          </div>
        </div>

        <div className="mt-4 space-y-2">
          {Object.entries(coverage).map(([dept, ready]) => (
            <div key={dept} className="flex items-center justify-between rounded-lg border border-neutral-100 px-3 py-2 dark:border-neutral-800">
              <span className="text-sm capitalize text-neutral-700 dark:text-neutral-300">{dept.replace(/_/g, ' ')}</span>
              <StatusBadge status={ready ? 'success' : 'warning'}>
                {ready ? 'Covered' : 'Missing'}
              </StatusBadge>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
