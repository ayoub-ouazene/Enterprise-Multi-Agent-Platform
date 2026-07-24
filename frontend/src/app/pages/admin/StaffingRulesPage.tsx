import { useAdminStaffingRules, useAdminDepartments } from '../../../api/hooks/useAdmin';
import { SectionCard } from './components/SectionCard';
import { ErrorState } from './components/ErrorState';
import { TableSkeleton } from './components/TableSkeleton';
import { StatusBadge } from './components/StatusBadge';

export function StaffingRulesPage() {
  const { data: rules, isLoading, error } = useAdminStaffingRules({ limit: 100 });
  const { data: departments } = useAdminDepartments();

  if (isLoading) return <TableSkeleton rows={5} />;
  if (error) return <ErrorState message="Failed to load staffing rules." />;

  return (
    <div className="space-y-4">
      <SectionCard title="Staffing Rules">
        <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900/50">
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Department</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Min Employees</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Effective</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {rules?.map((r) => {
                const dept = departments?.find((d) => d.id === r.department_id);
                return (
                  <tr key={r.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
                    <td className="px-4 py-2.5 font-medium text-neutral-900 dark:text-neutral-100">{dept?.name || '—'}</td>
                    <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">{r.minimum_active_employees}</td>
                    <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">
                      {new Date(r.effective_from).toLocaleDateString()}
                      {r.effective_to ? ` – ${new Date(r.effective_to).toLocaleDateString()}` : ' – Ongoing'}
                    </td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={r.is_active ? 'success' : 'neutral'}>
                        {r.is_active ? 'Active' : 'Inactive'}
                      </StatusBadge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {rules?.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-neutral-500 dark:text-neutral-400">No staffing rules found.</div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
