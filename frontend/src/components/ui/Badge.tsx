import { type HTMLAttributes } from 'react';
import { clsx } from 'clsx';

export type BadgeVariant = 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export function Badge({ variant = 'default', className, children, ...props }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        {
          'bg-gray-100 text-gray-800': variant === 'default',
          'bg-primary-100 text-primary-800': variant === 'primary',
          'bg-success-100 text-success-800': variant === 'success',
          'bg-warning-100 text-warning-800': variant === 'warning',
          'bg-danger-100 text-danger-800': variant === 'danger',
          'bg-blue-100 text-blue-800': variant === 'info',
        },
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
