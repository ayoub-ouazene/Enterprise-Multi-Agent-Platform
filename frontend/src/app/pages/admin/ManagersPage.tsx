import { useAdminEmployees, useAdminDepartments } from '../../../api/hooks/useAdmin';
import { SectionCard } from './components/SectionCard';
import { ErrorState } from './components/ErrorState';
import { TableSkeleton } from './components/TableSkeleton';
import { Star } from 'lucide-react';

export function ManagersPage() {
  const { data: employees, isLoading, error } = useAdminEmployees({ limit: 500 });
  const { data: departments } = useAdminDepartments();

  const managers = employees?.filter((e) => e.manager_employee_id !== null) ?? [];
  const employeesById = new Map(employees?.map((e) => [e.id, e]) ?? []);

  if (isLoading) return <TableSkeleton rows={4} />;
  if (error) return <ErrorState message="Failed to load managers." />;

  return (
    <div className="space-y-4">
      <SectionCard title="Managers" description={`${managers.length} employee${managers.length !== 1 ? 's' : ''} with an assigned manager`}>
        <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900/50">
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Employee</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Manager</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Department</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {managers.map((emp) => {
                const manager = emp.manager_employee_id ? employeesById.get(emp.manager_employee_id) : null;
                const dept = departments?.find((d) => d.id === emp.department_id);
                return (
                  <tr key={emp.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <Star size={12} className="text-amber-500" />
                        <span className="font-medium text-neutral-900 dark:text-neutral-100">{emp.employee_code}</span>
                      </div>
                      <p className="mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">{emp.job_title || '—'}</p>
                    </td>
                    <td className="px-4 py-2.5 text-neutral-700 dark:text-neutral-300">
                      {manager ? `${manager.employee_code} (${manager.job_title || '—'})` : '—'}
                    </td>
                    <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">{dept?.name || '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {managers.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-neutral-500 dark:text-neutral-400">
              No managers assigned yet.
            </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
