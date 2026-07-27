import { useState } from 'react';
import { CheckCircle2, Power, Users, ShieldCheck, AlertCircle } from 'lucide-react';
import { useAdminDepartments, useUpdateDepartment, useAdminEmployees } from '../../api/hooks/useOnboarding';
import type { OnboardingStatusDetailed, AdminDepartmentResponse } from '../../api/types';
import { Button } from '../../components/ui/Button';
import { Skeleton } from '../../components/layout/Skeleton';
import { Alert } from '../../components/ui/Alert';
import { clsx } from 'clsx';

interface DepartmentsStepProps {
  status: OnboardingStatusDetailed;
}

const deptMeta: Record<string, { icon: React.ReactNode; label: string; description: string }> = {
  customer_support: { icon: <Users size={16} />, label: 'Customer Support', description: 'Handles customer tickets and issues.' },
  hr: { icon: <Users size={16} />, label: 'Human Resources', description: 'Manages employees, leave, and staffing.' },
  it: { icon: <ShieldCheck size={16} />, label: 'Information Technology', description: 'Manages assets, software, and support.' },
  finance: { icon: <ShieldCheck size={16} />, label: 'Finance', description: 'Budgets and financial planning.' },
  procurement: { icon: <Users size={16} />, label: 'Procurement', description: 'Suppliers and purchasing.' },
};

export function DepartmentsStep({ status }: DepartmentsStepProps) {
  const { data: departments, isLoading } = useAdminDepartments();
  const { data: employees } = useAdminEmployees({ limit: 200 });
  const updateDept = useUpdateDepartment();
  const [pending, setPending] = useState<string | null>(null);

  const enabledItem = status.items.find((i) => i.requirement === 'enabled_departments');

  async function toggleDepartment(dept: AdminDepartmentResponse) {
    setPending(dept.id);
    try {
      await updateDept.mutateAsync({ id: dept.id, body: { is_active: !dept.is_active } });
    } finally {
      setPending(null);
    }
  }

  const empCounts = new Map<string, number>();
  employees?.forEach((e) => {
    if (e.department_id) {
      empCounts.set(e.department_id, (empCounts.get(e.department_id) ?? 0) + 1);
    }
  });

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">Departments</h2>
        <p className="text-xs text-neutral-500 dark:text-neutral-400">Activate the departments your company needs.</p>
      </div>

      {enabledItem?.satisfied ? (
        <Alert variant="success" title="Departments configured">
          {enabledItem.details}
        </Alert>
      ) : (
        <Alert variant="info" title="Enable at least one department">
          {enabledItem?.details}
        </Alert>
      )}

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton variant="rect" className="h-28 w-full" />
          <Skeleton variant="rect" className="h-28 w-full" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {departments?.map((dept) => {
            const meta = deptMeta[dept.department_type] ?? { icon: <Users size={16} />, label: dept.name, description: '' };
            const empCount = empCounts.get(dept.id) ?? 0;
            return (
              <div
                key={dept.id}
                className={clsx(
                  'flex items-start gap-4 rounded-lg border p-4 transition-colors',
                  dept.is_active
                    ? 'border-primary-200 bg-primary-50/50 dark:border-primary-800 dark:bg-primary-900/20'
                    : 'border-neutral-200 bg-white dark:border-neutral-700 dark:bg-neutral-800'
                )}
              >
                <div className={clsx(
                  'flex h-10 w-10 shrink-0 items-center justify-center rounded-md',
                  dept.is_active ? 'bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-300' : 'bg-neutral-100 text-neutral-500 dark:bg-neutral-700 dark:text-neutral-400'
                )}>
                  {meta.icon}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{meta.label}</h3>
                    {dept.is_active && <CheckCircle2 size={14} className="text-success-500" />}
                    {!dept.is_active && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2 py-0.5 text-xs text-neutral-600 dark:bg-neutral-700 dark:text-neutral-300">
                        <AlertCircle size={10} />
                        Inactive
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">{meta.description}</p>
                  <p className="mt-1 text-xs text-neutral-400 dark:text-neutral-500">{empCount} employee(s)</p>
                </div>
                <Button
                  variant={dept.is_active ? 'secondary' : 'primary'}
                  size="sm"
                  isLoading={pending === dept.id}
                  disabled={pending === dept.id || (dept.is_active && empCount > 0)}
                  onClick={() => toggleDepartment(dept)}
                >
                  {dept.is_active ? (
                    <span className="inline-flex items-center gap-1.5">
                      <Power size={12} />
                      Disable
                    </span>
                  ) : (
                    'Enable'
                  )}
                </Button>
                {dept.is_active && empCount > 0 && <span className="sr-only">Cannot disable a department with provisioned employees.</span>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
