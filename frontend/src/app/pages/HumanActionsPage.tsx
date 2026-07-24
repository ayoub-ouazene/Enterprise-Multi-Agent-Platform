import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, ArrowUpRight, Clock, ShieldAlert } from 'lucide-react';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Skeleton } from '../../components/layout/Skeleton';
import { StatusDot } from '../../components/layout/MetricCard';
import { Alert } from '../../components/ui/Alert';
import { EmptyState } from '../../components/ui/EmptyState';
import { useHumanActions } from '../../api/hooks/useHumanActions';
import { getHumanActionStatusMeta } from '../../lib/status';
import { formatDate } from '../../lib/formatters';
import { ActionTypeBadge } from '../../human-action/components/ActionTypeBadge';

const tabs = [
  { label: 'Pending', value: 'pending' as const },
  { label: 'Overdue', value: 'overdue' as const },
  { label: 'All', value: 'all' as const },
];

type TabValue = typeof tabs[number]['value'];

export function HumanActionsPage() {
  const [tab, setTab] = useState<TabValue>('pending');
  const statusParam = tab === 'all' ? undefined : tab === 'overdue' ? undefined : tab;
  const { data: actions, isLoading, error } = useHumanActions({ status: statusParam, limit: 50 });

  const filtered = useMemo(() => {
    let list = actions ?? [];
    if (tab === 'overdue') {
      const now = new Date();
      list = list.filter((a) => a.status === 'pending' && a.due_date && new Date(a.due_date) < now);
      list.sort((a, b) => (new Date(a.due_date!).getTime()) - (new Date(b.due_date!).getTime()));
    } else if (tab === 'all') {
      list.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
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
            onClick={() => setTab(t.value)}
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
          {filtered.map((action) => (
            <HumanActionCard key={action.id} action={action} />
          ))}
        </div>
      ) : (
        <EmptyState
          title={tab === 'overdue' ? 'No overdue actions' : tab === 'all' ? 'No actions found' : 'No pending actions'}
          description={tab === 'all' ? 'Human actions will appear here when the system creates them.' : 'All caught up. Actions will appear here when needed.'}
        />
      )}
    </PageContainer>
  );
}

function HumanActionCard({ action }: { action: import('../../api/types').HumanActionSummary }) {
  const navigate = useNavigate();
  const now = new Date();
  const overdue = action.status === 'pending' && action.due_date ? new Date(action.due_date) < now : false;
  const meta = getHumanActionStatusMeta(action.status);
  const cat = overdue ? 'attention' : meta.category;

  return (
    <button
      onClick={() => navigate(`/app/human-actions/${action.id}`)}
      className="flex flex-col rounded-lg border border-neutral-200 bg-white p-4 text-left shadow-xs transition-colors hover:border-neutral-300 dark:border-neutral-800 dark:bg-neutral-800 dark:hover:border-neutral-700 sm:flex-row sm:items-start sm:justify-between sm:gap-4"
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
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
          {!action.can_respond && action.status === 'pending' && (
            <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-bold uppercase text-neutral-600 dark:bg-neutral-700 dark:text-neutral-300">
              <ShieldAlert size={10} />
              View Only
            </span>
          )}
        </div>
        <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">
          {action.description}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400">
          <ActionTypeBadge actionType={action.action_type} />
          {action.request_title && (
            <span className="max-w-[200px] truncate" title={action.request_title}>
              {action.request_title}
            </span>
          )}
          {action.due_date && (
            <span className={`inline-flex items-center gap-1 ${overdue ? 'font-semibold text-danger-600 dark:text-danger-400' : ''}`}>
              <Clock size={12} aria-hidden="true" />
              Due {formatDate(action.due_date)}
            </span>
          )}
        </div>
      </div>
      <div className="mt-3 flex shrink-0 items-center sm:mt-0">
        <span className="inline-flex items-center gap-1 rounded-md bg-primary-600 px-3 py-1.5 text-xs font-medium text-white">
          Open <ArrowUpRight size={12} aria-hidden="true" />
        </span>
      </div>
    </button>
  );
}
