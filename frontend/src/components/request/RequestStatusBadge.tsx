import { clsx } from 'clsx';
import { getRequestStatusMeta, statusCategoryStyles } from '../../lib/status';

interface RequestStatusBadgeProps {
  status: string;
  className?: string;
}

export function RequestStatusBadge({ status, className }: RequestStatusBadgeProps) {
  const meta = getRequestStatusMeta(status);
  const styles = statusCategoryStyles[meta.category];

  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        styles.badgeClass,
        className
      )}
    >
      {meta.label}
    </span>
  );
}
