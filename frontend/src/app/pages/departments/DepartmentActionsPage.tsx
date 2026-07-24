import { useParams, useNavigate } from 'react-router-dom';
import { Hand } from 'lucide-react';
import { PageContainer, PageHeader } from '../../../components/layout/PageContainer';
import { StatusBadge } from '../admin/components/StatusBadge';
import { ErrorState } from '../admin/components/ErrorState';
import { useDepartmentActions } from '../../../api/hooks/useDepartments';
import { getDepartmentMeta, slugToDepartmentType } from '../../../lib/departments';
import { relativeTime } from '../../../lib/formatters';

export function DepartmentActionsPage() {
  const { deptSlug } = useParams<{ deptSlug: string }>();
  const navigate = useNavigate();
  const deptType = deptSlug ? slugToDepartmentType(deptSlug) : undefined;
  const meta = deptType ? getDepartmentMeta(deptType) : undefined;

  const { data: actions, isLoading, error } = useDepartmentActions(deptType ?? '', {
    status: 'pending',
    limit: 50,
  });

  if (!deptType || !meta) {
    return (
      <PageContainer>
        <ErrorState message="The department does not exist." />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader title="Human Actions" description={`Pending actions for ${meta.label}`} />

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-md bg-neutral-100 dark:bg-neutral-800" />
          ))}
        </div>
      )}

      {error && <ErrorState message="Failed to load actions. Please try again." />}

      {!isLoading && !error && (
        <div className="space-y-2">
          {actions && actions.length > 0 ? (
            actions.map((action) => (
              <button
                key={action.id}
                onClick={() => navigate(`/app/human-actions/${action.id}`)}
                className="flex w-full items-center justify-between rounded-md border border-neutral-200 bg-white px-4 py-3 text-left transition-colors hover:border-neutral-300 dark:border-neutral-800 dark:bg-neutral-800 dark:hover:border-neutral-700"
              >
                <div className="flex items-start gap-3">
                  <Hand size={16} className="mt-0.5 text-warning-500" />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-100">{action.title}</p>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400">{action.action_type} &middot; {relativeTime(action.created_at)}</p>
                  </div>
                </div>
                <StatusBadge status="warning">Pending</StatusBadge>
              </button>
            ))
          ) : (
            <p className="text-sm text-neutral-500 dark:text-neutral-400">No pending actions.</p>
          )}
        </div>
      )}
    </PageContainer>
  );
}
