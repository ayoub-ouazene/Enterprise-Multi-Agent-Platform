import { useState } from 'react';
import { Search, AlertTriangle } from 'lucide-react';
import {
  useAdminEmployees,
  useDeactivateEmployee,
  useAdminDepartments,
} from '../../../api/hooks/useAdmin';
import { ErrorState } from './components/ErrorState';
import { TableSkeleton } from './components/TableSkeleton';
import { StatusBadge } from './components/StatusBadge';
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
      {confirmDeactivate && (
        <ConfirmDialog
          title="Deactivate Employee"
          message="This will set the employee status to TERMINATED. Are you sure?"
          confirmLabel="Deactivate"
          confirmVariant="danger"
          onConfirm={() => {
            deactivate.mutate(confirmDeactivate, { onSuccess: () => setConfirmDeactivate(null) });
          }}
          onCancel={() => setConfirmDeactivate(null)}
          isPending={deactivate.isPending}
        />
      )}
    </div>
  );
}

function ConfirmDialog({
  title,
  message,
  confirmLabel,
  confirmVariant,
  onConfirm,
  onCancel,
  isPending,
}: {
  title: string;
  message: string;
  confirmLabel: string;
  confirmVariant?: 'danger' | 'primary';
  onConfirm: () => void;
  onCancel: () => void;
  isPending: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-xl bg-white p-5 shadow-lg dark:bg-neutral-800">
        <div className="flex items-start gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-600 dark:bg-amber-900/30">
            <AlertTriangle size={16} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{title}</h3>
            <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">{message}</p>
          </div>
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className={`rounded-md px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50 ${
              confirmVariant === 'danger'
                ? 'bg-rose-600 hover:bg-rose-700'
                : 'bg-primary-600 hover:bg-primary-700'
            }`}
          >
            {isPending ? 'Processing...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
