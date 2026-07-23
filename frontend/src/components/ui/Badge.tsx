import { type HTMLAttributes } from 'react';
import { clsx } from 'clsx';
import { type StatusCategory, statusCategoryStyles } from '../../lib/status';

export type BadgeVariant = 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info';

const legacyMap: Record<BadgeVariant, string> = {
  default: 'bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200',
  primary: 'bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200',
  success: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-200',
  warning: 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-200',
  danger:  'bg-danger-100 text-danger-800 dark:bg-danger-900 dark:text-danger-200',
  info:    'bg-info-100 text-info-800 dark:bg-info-900 dark:text-info-200',
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  category?: StatusCategory;
}

export function Badge({ variant = 'default', category, className, children, ...props }: BadgeProps) {
  const classes = category
    ? statusCategoryStyles[category]?.badgeClass
    : legacyMap[variant];

  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        classes,
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
