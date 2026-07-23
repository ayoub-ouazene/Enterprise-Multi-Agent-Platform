import { clsx } from 'clsx';
import { RequestStatusBadge } from './RequestStatusBadge';
import type { BusinessRequestSummary, RequestPriority } from '../../api/types';

interface RequestSummaryCardProps {
  request: BusinessRequestSummary;
  onClick?: () => void;
  className?: string;
}

export function RequestSummaryCard({ request, onClick, className }: RequestSummaryCardProps) {
  return (
    <div
      className={clsx(
        'group rounded-lg border border-neutral-200 bg-white p-4 shadow-xs transition-all',
        'hover:border-neutral-300 hover:shadow-sm',
        'dark:border-neutral-800 dark:bg-neutral-800 dark:hover:border-neutral-700',
        onClick && 'cursor-pointer',
        className
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') onClick();
            }
          : undefined
      }
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-neutral-900 transition-colors group-hover:text-primary-600 dark:text-neutral-100 dark:group-hover:text-primary-400 truncate">
              {request.title}
            </h3>
          </div>

          <RequestMetaRow
            type={request.request_type}
            priority={request.priority}
            stage={request.current_stage}
            className="mt-1"
          />

          {request.summary && (
            <p className="mt-2 line-clamp-2 text-sm text-neutral-500 dark:text-neutral-400">
              {request.summary}
            </p>
          )}
        </div>
        <RequestStatusBadge status={request.status} />
      </div>
    </div>
  );
}

interface RequestMetaRowProps {
  type: string;
  priority: RequestPriority;
  stage: string;
  className?: string;
}

export function RequestMetaRow({ type, priority, stage, className }: RequestMetaRowProps) {
  const priorityDot: Record<RequestPriority, string> = {
    low: 'bg-info-400',
    normal: 'bg-success-400',
    high: 'bg-warning-400',
    urgent: 'bg-danger-500',
  };

  return (
    <div className={clsx('flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-neutral-500 dark:text-neutral-400', className)}>
      <span>{type}</span>
      <span className="hidden sm:inline">•</span>
      <span className="hidden sm:inline">{stage}</span>
      <span className="hidden sm:inline">•</span>
      <span className="flex items-center gap-1.5 capitalize">
        <span className={clsx('inline-block h-2 w-2 rounded-full', priorityDot[priority])} aria-hidden="true" />
        {priority}
      </span>
    </div>
  );
}
