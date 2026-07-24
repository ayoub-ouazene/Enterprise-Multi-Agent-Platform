import { useParams } from 'react-router-dom';
import { PageContainer, PageHeader, Section } from '../../../components/layout/PageContainer';
import { ErrorState } from '../admin/components/ErrorState';
import { useDepartments } from '../../../api/hooks/useDepartments';
import { getDepartmentMeta, slugToDepartmentType } from '../../../lib/departments';
import { ShieldCheck, AlertTriangle } from 'lucide-react';

export function DepartmentSettingsPage() {
  const { deptSlug } = useParams<{ deptSlug: string }>();
  const deptType = deptSlug ? slugToDepartmentType(deptSlug) : undefined;
  const meta = deptType ? getDepartmentMeta(deptType) : undefined;

  const { data: departments, isLoading } = useDepartments();
  const department = departments?.find((d) => d.department_type === deptType);

  if (!deptType || !meta) {
    return (
      <PageContainer>
        <ErrorState message="The department does not exist." />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader title="Settings" description={`${meta.label} workspace settings`} />

      <Section title="Department Information">
        {isLoading ? (
          <div className="space-y-2">
            <div className="h-4 w-32 animate-pulse rounded bg-neutral-100 dark:bg-neutral-700" />
            <div className="h-4 w-48 animate-pulse rounded bg-neutral-100 dark:bg-neutral-700" />
          </div>
        ) : department ? (
          <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium text-neutral-500 dark:text-neutral-400">Name</dt>
              <dd className="text-sm text-neutral-900 dark:text-neutral-100">{department.name}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-neutral-500 dark:text-neutral-400">Type</dt>
              <dd className="text-sm text-neutral-900 dark:text-neutral-100">{meta.label}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-neutral-500 dark:text-neutral-400">Status</dt>
              <dd className="text-sm text-neutral-900 dark:text-neutral-100">
                {department.is_active ? (
                  <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                    <ShieldCheck size={12} /> Active
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-red-600 dark:text-red-400">
                    <AlertTriangle size={12} /> Inactive
                  </span>
                )}
              </dd>
            </div>
          </dl>
        ) : (
          <p className="text-sm text-neutral-500 dark:text-neutral-400">Department information unavailable.</p>
        )}
      </Section>

      <div className="mt-4">
        <Section title="Permissions">
          <p className="text-sm text-neutral-600 dark:text-neutral-300">
            Department managers can view requests, human actions, and activity scoped to their department.
            Company accounts have unrestricted access to all department workspaces.
          </p>
        </Section>
      </div>
    </PageContainer>
  );
}
