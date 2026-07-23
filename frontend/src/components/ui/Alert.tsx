import { clsx } from 'clsx';
import { AlertTriangle, CheckCircle, Info, XCircle, type LucideIcon } from 'lucide-react';
import { type HTMLAttributes } from 'react';

export type AlertVariant = 'info' | 'success' | 'warning' | 'error';

const iconMap: Record<AlertVariant, LucideIcon> = {
  info: Info,
  success: CheckCircle,
  warning: AlertTriangle,
  error: XCircle,
};

const stylesMap: Record<AlertVariant, string> = {
  info: 'border-info-200 bg-info-50 text-info-900 dark:border-info-800 dark:bg-info-950 dark:text-info-100',
  success: 'border-success-200 bg-success-50 text-success-900 dark:border-success-800 dark:bg-success-950 dark:text-success-100',
  warning: 'border-warning-200 bg-warning-50 text-warning-900 dark:border-warning-800 dark:bg-warning-950 dark:text-warning-100',
  error: 'border-danger-200 bg-danger-50 text-danger-900 dark:border-danger-800 dark:bg-danger-950 dark:text-danger-100',
};

interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  variant?: AlertVariant;
  title?: string;
}

export function Alert({ variant = 'info', title, className, children, ...props }: AlertProps) {
  const Icon = iconMap[variant];

  return (
    <div
      role="alert"
      className={clsx(
        'rounded-lg border p-4',
        stylesMap[variant],
        className
      )}
      {...props}
    >
      <div className="flex items-start gap-3">
        <Icon size={18} className="mt-0.5 shrink-0 opacity-80" aria-hidden="true" />
        <div className="flex-1">
          {title && <h3 className="mb-1 text-sm font-semibold">{title}</h3>}
          <div className="text-sm leading-relaxed">{children}</div>
        </div>
      </div>
    </div>
  );
}
