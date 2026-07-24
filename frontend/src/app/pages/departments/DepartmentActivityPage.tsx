import { useParams } from 'react-router-dom';
import { PageContainer, PageHeader } from '../../../components/layout/PageContainer';
import { ErrorState } from '../admin/components/ErrorState';
import { useDepartmentActivity } from '../../../api/hooks/useDepartments';
import { getDepartmentMeta, slugToDepartmentType } from '../../../lib/departments';
import { relativeTime } from '../../../lib/formatters';

export function DepartmentActivityPage() {
  const { deptSlug } = useParams<{ deptSlug: string }>();
  const deptType = deptSlug ? slugToDepartmentType(deptSlug) : undefined;
  const meta = deptType ? getDepartmentMeta(deptType) : undefined;

  const { data: events, isLoading, error } = useDepartmentActivity(deptType ?? '', 30);

  if (!deptType || !meta) {
    return (
      <PageContainer>
        <ErrorState message="The department does not exist." />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader title="Activity" description={`Recent workflow events for ${meta.label}`} />

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-md bg-neutral-100 dark:bg-neutral-800" />
          ))}
        </div>
      )}

      {error && <ErrorState message="Failed to load activity. Please try again." />}

      {!isLoading && !error && (
        <div className="relative space-y-3">
          <div className="absolute left-3 top-2 bottom-2 w-px bg-neutral-200 dark:bg-neutral-700" aria-hidden="true" />
          {events && events.length > 0 ? (
            events.map((event) => (
              <div key={event.id} className="relative flex gap-3 pl-1">
                <div className="z-10 mt-1.5 h-2.5 w-2.5 rounded-full bg-primary-400 ring-4 ring-white dark:ring-neutral-900" />
                <div className="min-w-0 flex-1 rounded-md border border-neutral-200 bg-white p-3 dark:border-neutral-800 dark:bg-neutral-800">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{event.title}</h4>
                    <span className="shrink-0 text-xs text-neutral-500 dark:text-neutral-400">{relativeTime(event.created_at)}</span>
                  </div>
                  <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">{event.message}</p>
                  <div className="mt-1 text-xs text-neutral-400 dark:text-neutral-500">
                    {event.actor_label} &middot; {event.event_type}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-neutral-500 dark:text-neutral-400">No recent activity.</p>
          )}
        </div>
      )}
    </PageContainer>
  );
}
