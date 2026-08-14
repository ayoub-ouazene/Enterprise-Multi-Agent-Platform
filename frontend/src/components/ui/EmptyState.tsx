import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ title = 'Nothing here', description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center" role="region" aria-label="Empty state">
      <span className="empty-float mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10 text-indigo-400/60 dark:text-indigo-400/70">
        <Inbox size={32} aria-hidden="true" />
      </span>
      <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{title}</h3>
      {description && <p className="mt-1 max-w-xs text-sm text-neutral-500 dark:text-neutral-400">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
