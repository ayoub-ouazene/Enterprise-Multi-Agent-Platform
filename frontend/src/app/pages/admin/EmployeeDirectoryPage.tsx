import { useState } from 'react';
import { Search } from 'lucide-react';
import {
  useAdminEmployees,
  useDeactivateEmployee,
  useAdminDepartments,
} from '../../../api/hooks/useAdmin';
import { ErrorState } from './components/ErrorState';
import { TableSkeleton } from './components/TableSkeleton';
import { StatusBadge } from './components/StatusBadge';
import { ConfirmDialog } from '../../../components/ui/ConfirmDialog';
import { useAuthContext } from '../../../auth/hooks/useAuthContext';
import { isCompanyAccount, isDepartmentManager } from '../../../auth/permissions';

export function EmployeeDirectoryPage() {
  const { user } = useAuthContext();
  const [search, setSearch] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [confirmDeactivate, setConfirmDeactivate] = useState<string | null>(null);

  const { data: employees, isLoading, error } = useAdminEmployees({
    q: search || undefined,
    department_id: deptFilter || undefined,
    limit: 100,
  });
  const { data: departments } = useAdminDepartments();
  const deactivate = useDeactivateEmployee();

  const canWrite = isCompanyAccount(user) || isDepartmentManager(user);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative max-w-sm">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-400" />
          <input
            type="text"
            placeholder="Search employees..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md border border-neutral-300 py-1.5 pl-9 pr-3 text-sm text-neutral-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
          />
        </div>
        <div className="flex items-center gap-2">
          <select
            value={deptFilter}
            onChange={(e) => setDeptFilter(e.target.value)}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm text-neutral-900 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
          >
            <option value="">All Departments</option>
            {departments?.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>

        </div>
      </div>

      {isLoading && <TableSkeleton rows={5} />}
      {error && <ErrorState message="Failed to load employees." />}
      {employees && (
        <div className="overflow-x-auto rounded-xl border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900/50">
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Code</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Job Title</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Status</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Department</th>
                <th className="px-4 py-2.5 text-right font-medium text-neutral-600 dark:text-neutral-400">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {employees.map((emp) => {
                const dept = departments?.find((d) => d.id === emp.department_id);
                return (
                  <tr key={emp.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
                    <td className="px-4 py-2.5 font-medium text-neutral-900 dark:text-neutral-100">{emp.employee_code}</td>
                    <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">{emp.job_title || '—'}</td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={emp.employment_status === 'active' ? 'success' : 'neutral'}>
                        {emp.employment_status}
                      </StatusBadge>
                    </td>
                    <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">{dept?.name || '—'}</td>
                    <td className="px-4 py-2.5 text-right">
                      {canWrite && emp.employment_status === 'active' && (
                        <button
                          onClick={() => setConfirmDeactivate(emp.id)}
                          className="text-xs font-medium text-rose-600 hover:underline dark:text-rose-400"
                        >
                          Deactivate
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {employees.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-neutral-500 dark:text-neutral-400">
              No employees found.
            </div>
          )}
        </div>
      )}

      {/* Deactivate confirmation */}
      <ConfirmDialog
        title="Deactivate Employee"
        message="This will set the employee status to TERMINATED. Are you sure?"
        confirmLabel="Deactivate"
        confirmVariant="danger"
        isOpen={!!confirmDeactivate}
        isPending={deactivate.isPending}
        onConfirm={() => {
          if (confirmDeactivate) {
            deactivate.mutate(confirmDeactivate, { onSuccess: () => setConfirmDeactivate(null) });
          }
        }}
        onCancel={() => setConfirmDeactivate(null)}
      />
    </div>
  );
}
