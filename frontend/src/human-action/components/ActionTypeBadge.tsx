import { clsx } from 'clsx';
import { getActionTypeConfig } from '../registry';

interface ActionTypeBadgeProps {
  actionType: string;
  className?: string;
}

const actionColorMap: Record<string, string> = {
  supplier_selection: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  technician_action: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
  onboarding_confirmation: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  information_request: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  identity_verification: 'bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-200',
};

export function ActionTypeBadge({ actionType, className }: ActionTypeBadgeProps) {
  const config = getActionTypeConfig(actionType);
  const colorClass = actionColorMap[actionType] ?? 'bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200';

  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        colorClass,
        className
      )}
      title={config.description}
    >
      {config.label}
    </span>
  );
}
