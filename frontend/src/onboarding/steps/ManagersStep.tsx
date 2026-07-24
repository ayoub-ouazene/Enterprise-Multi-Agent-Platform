import { useState } from 'react';
import { UserCheck, Search } from 'lucide-react';
import { useAdminEmployees, useUpdateEmployee, useAdminDepartments } from '../../api/hooks/useOnboarding';
import type { OnboardingStatusDetailed, AdminEmployeeResponse } from '../../api/types';
import { Button } from '../../components/ui/Button';
import { Skeleton } from '../../components/layout/Skeleton';
import { Alert } from '../../components/ui/Alert';

interface ManagersStepProps {
  status: OnboardingStatusDetailed;
}

export function ManagersStep({ status }: ManagersStepProps) {
  const [search, setSearch] = useState('');
  const [selectedEmployee, setSelectedEmployee] = useState<string | null>(null);
  const [managerId, setManagerId] = useState<string>('');
  const { data: employees, isLoading } = useAdminEmployees({ limit: 200 });
  const { data: departments } = useAdminDepartments();
  const updateEmployee = useUpdateEmployee();

  const managerItem = status.items.find((i) => i.requirement === 'managers');

  const deptMap = new Map(departments?.map((d) => [d.id, d]) ?? []);

  function getFilteredEmployees(): AdminEmployeeResponse[] | undefined {
    if (!employees) return undefined;
    const q = search.trim().toLowerCase();
    if (!q) return employees;
    return employees.filter(
      (e) =>
        e.employee_code.toLowerCase().includes(q) ||
        (e.job_title ?? '').toLowerCase().includes(q)
    );
  }

  async function assignManager(employeeId: string, managerEmployeeId: string) {
    if (!managerEmployeeId) return;
    await updateEmployee.mutateAsync({
      id: employeeId,
      body: { manager_employee_id: managerEmployeeId },
    });
    setSelectedEmployee(null);
    setManagerId('');
  }

  const filtered = getFilteredEmployees();

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-300">
          <UserCheck size={20} />
        </div>
        <div>
          <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">Managers</h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">Assign a manager to each enabled department.</p>
        </div>
      </div>

      {managerItem?.satisfied ? (
        <Alert variant="success" title="Managers assigned">
          {managerItem.details ?? 'All enabled departments have managers.'}
        </Alert>
      ) : (
        <Alert variant="warning" title="Managers missing">
          {managerItem?.details ?? 'Assign at least one manager per enabled department.'}
        </Alert>
      )}

      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search employees..."
          className="w-full rounded-md border border-neutral-300 bg-white py-2 pl-9 pr-3 text-sm text-neutral-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-neutral-600 dark:bg-neutral-700 dark:text-neutral-100"
        />
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton variant="rect" className="h-16 w-full" />
          <Skeleton variant="rect" className="h-16 w-full" />
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {filtered?.map((emp) => {
            const dept = emp.department_id ? deptMap.get(emp.department_id) : undefined;
            const isEditing = selectedEmployee === emp.id;
            return (
              <div
                key={emp.id}
                className="rounded-lg border border-neutral-200 bg-white p-3 dark:border-neutral-700 dark:bg-neutral-800"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{emp.employee_code}</p>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400">
                      {emp.job_title ?? 'No title'} {dept ? `· ${dept.name}` : ''}
                    </p>
                  </div>
                  <div className="text-right">
                    {emp.manager_employee_id ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-success-100 px-2 py-0.5 text-xs font-medium text-success-700 dark:bg-success-900 dark:text-success-300">
                        <UserCheck size={10} />
                        Has Manager
                      </span>
                    ) : (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => { setSelectedEmployee(emp.id); setManagerId(''); }}
                      >
                        Assign
                      </Button>
                    )}
                  </div>
                </div>

                {isEditing && (
                  <div className="mt-3 flex items-center gap-2 border-t border-neutral-100 pt-3 dark:border-neutral-700">
                    <select
                      value={managerId}
                      onChange={(e) => setManagerId(e.target.value)}
                      className="flex-1 rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-sm text-neutral-900 focus:border-primary-500 focus:outline-none dark:border-neutral-600 dark:bg-neutral-700 dark:text-neutral-100"
                    >
                      <option value="">Select manager...</option>
                      {employees
                        ?.filter((e) => e.id !== emp.id)
                        .map((e) => (
                          <option key={e.id} value={e.id}>
                            {e.employee_code} {e.job_title ? `- ${e.job_title}` : ''}
                          </option>
                        ))}
                    </select>
                    <Button
                      size="sm"
                      onClick={() => assignManager(emp.id, managerId)}
                      disabled={!managerId || updateEmployee.isPending}
                      isLoading={updateEmployee.isPending}
                    >
                      Save
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => { setSelectedEmployee(null); setManagerId(''); }}
                    >
                      Cancel
                    </Button>
                  </div>
                )}
              </div>
            );
          })}
          {filtered?.length === 0 && (
            <p className="text-sm text-neutral-500 dark:text-neutral-400">No employees match your search.</p>
          )}
        </div>
      )}
    </div>
  );
}
