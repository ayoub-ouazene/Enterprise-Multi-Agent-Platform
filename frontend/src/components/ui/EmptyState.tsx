import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ title = 'Nothing here', description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center" role="region" aria-label="Empty state">
      <Inbox size={40} className="mb-4 text-neutral-300 dark:text-neutral-600" aria-hidden="true" />
      <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{title}</h3>
      {description && <p className="mt-1 max-w-xs text-sm text-neutral-500 dark:text-neutral-400">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
