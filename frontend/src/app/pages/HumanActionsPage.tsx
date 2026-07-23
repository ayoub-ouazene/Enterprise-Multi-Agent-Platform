import { useMemo, useState } from 'react';
import { AlertTriangle, ArrowUpRight, CalendarClock, Clock } from 'lucide-react';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Skeleton } from '../../components/layout/Skeleton';
import { StatusDot } from '../../components/layout/MetricCard';
import { Alert } from '../../components/ui/Alert';
import { EmptyState } from '../../components/ui/EmptyState';
import { useHumanActions } from '../../api/hooks/useHumanActions';
import { getHumanActionStatusMeta } from '../../lib/status';
import { formatDate } from '../../lib/formatters';

const tabs = [
  { label: 'Pending', value: 'pending' },
  { label: 'Overdue', value: 'overdue' },
  { label: 'All', value: 'all' },
];

export function HumanActionsPage() {
  const [tab, setTab] = useState<'pending' | 'overdue' | 'all'>('pending');
  const statusParam = tab === 'all' ? undefined : tab === 'overdue' ? undefined : tab;
  const { data: actions, isLoading, error } = useHumanActions({ status: statusParam, limit: 50 });

  const filtered = useMemo(() => {
    let list = actions ?? [];
    if (tab === 'overdue') {
      list = list.filter((a) => a.due_date && new Date(a.due_date) < new Date());
      list.sort((a, b) => (new Date(a.due_date!).getTime()) - (new Date(b.due_date!).getTime()));
    }
    return list;
  }, [actions, tab]);

  return (
    <PageContainer>
      <PageHeader title="Human Actions" description="Tasks requiring human intervention" />

      <div className="mb-4 flex gap-2" role="tablist" aria-label="Human action filters">
        {tabs.map((t) => (
          <button
            key={t.value}
            role="tab"
            aria-selected={tab === t.value}
            onClick={() => setTab(t.value as typeof tab)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              tab === t.value
                ? 'bg-neutral-900 text-white dark:bg-primary-600 dark:text-white'
                : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-400 dark:hover:bg-neutral-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && (
        <Alert variant="error" title="Failed to load human actions">
          {error instanceof Error ? error.message : 'Please try again later.'}
        </Alert>
      )}

      {isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} variant="rect" className="h-24 w-full" />
          ))}
        </div>
      ) : filtered.length > 0 ? (
        <div className="space-y-3">
          {filtered.map((action) => <HumanActionCard key={action.id} action={action} />)}
        </div>
      ) : (
        <div className="rounded-lg border border-neutral-200 bg-white p-8 shadow-xs dark:border-neutral-800 dark:bg-neutral-800">
          <EmptyState
            title={tab === 'overdue' ? 'No overdue actions' : 'No pending actions'}
            description="All caught up. Actions will appear here when needed."
          />
        </div>
      )}
    </PageContainer>
  );
}

function HumanActionCard({ action }: { action: import('../../api/types').HumanActionSummary }) {
  const overdue = action.due_date ? new Date(action.due_date) < new Date() : false;
  const meta = getHumanActionStatusMeta(action.status);
  const cat = overdue ? 'attention' : meta.category;

  return (
    <div className="flex flex-col rounded-lg border border-neutral-200 bg-white p-4 shadow-xs transition-colors hover:border-neutral-300 dark:border-neutral-800 dark:bg-neutral-800 dark:hover:border-neutral-700 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <StatusDot category={cat} />
          <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            {action.title}
          </h3>
          {overdue && (
            <span className="inline-flex items-center gap-1 rounded-full bg-danger-50 px-2 py-0.5 text-[10px] font-bold uppercase text-danger-700 dark:bg-danger-900 dark:text-danger-300">
              <AlertTriangle size={10} />
              Overdue
            </span>
          )}
        </div>
        <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">
          {action.description}
        </p>
        <div className="mt-2 flex items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400">
          <span className="inline-flex items-center gap-1">
            <CalendarClock size={12} aria-hidden="true" />
            {action.action_type}
          </span>
          {action.due_date && (
            <span className={`inline-flex items-center gap-1 ${overdue ? 'text-danger-600 dark:text-danger-400 font-semibold' : ''}`}>
              <Clock size={12} aria-hidden="true" />
              Due {formatDate(action.due_date)}
            </span>
          )}
        </div>
      </div>
      <div className="mt-3 flex sm:mt-0">
        <button className="inline-flex items-center gap-1 rounded-md bg-primary-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-neutral-900">
          Open <ArrowUpRight size={12} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
