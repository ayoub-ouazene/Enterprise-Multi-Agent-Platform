import { type HTMLAttributes } from 'react';
import { clsx } from 'clsx';

export type AlertVariant = 'info' | 'success' | 'warning' | 'error';

interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  variant?: AlertVariant;
  title?: string;
}

export function Alert({ variant = 'info', title, className, children, ...props }: AlertProps) {
  return (
    <div
      role="alert"
      className={clsx(
        'rounded-md border p-4',
        {
          'border-blue-200 bg-blue-50 text-blue-800': variant === 'info',
          'border-success-200 bg-success-50 text-success-800': variant === 'success',
          'border-warning-200 bg-warning-50 text-warning-800': variant === 'warning',
          'border-danger-200 bg-danger-50 text-danger-800': variant === 'error',
        },
        className
      )}
      {...props}
    >
      {title && <h3 className="mb-1 text-sm font-medium">{title}</h3>}
      <div className="text-sm">{children}</div>
    </div>
  );
}
