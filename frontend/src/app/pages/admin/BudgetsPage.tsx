import { useAdminBudgets } from '../../../api/hooks/useAdmin';
import { SectionCard } from './components/SectionCard';
import { ErrorState } from './components/ErrorState';
import { TableSkeleton } from './components/TableSkeleton';
import { StatusBadge } from './components/StatusBadge';

export function BudgetsPage() {
  const { data, isLoading, error } = useAdminBudgets({ limit: 100 });

  if (isLoading) return <TableSkeleton rows={5} />;
  if (error) return <ErrorState message="Failed to load budgets." />;

  return (
    <div className="space-y-4">
      <SectionCard title="Budgets">
        <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900/50">
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Name</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Type</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Period</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Allocated</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Available</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {data?.map((b) => (
                <tr key={b.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
                  <td className="px-4 py-2.5 font-medium text-neutral-900 dark:text-neutral-100">{b.name}</td>
                  <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400 capitalize">{b.budget_type.replace(/_/g, ' ')}</td>
                  <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">
                    {new Date(b.period_start).toLocaleDateString()} – {new Date(b.period_end).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2.5 text-neutral-700 dark:text-neutral-300">
                    {b.currency} {Number(b.allocated_amount).toLocaleString()}
                  </td>
                  <td className="px-4 py-2.5 text-neutral-700 dark:text-neutral-300">
                    {b.currency} {Number(b.available_amount).toLocaleString()}
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={b.status === 'active' ? 'success' : b.status === 'draft' ? 'neutral' : 'warning'}>
                      {b.status}
                    </StatusBadge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data?.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-neutral-500 dark:text-neutral-400">No budgets found.</div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
