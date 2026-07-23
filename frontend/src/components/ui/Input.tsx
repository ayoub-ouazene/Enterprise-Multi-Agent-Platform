import { type InputHTMLAttributes, type ReactNode, forwardRef } from 'react';
import { clsx } from 'clsx';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  icon?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  function Input({ label, error, helperText, className, id, icon, ...props }, ref) {
    const inputId = id ?? props.name;
    const errorId = error ? `${inputId}-error` : undefined;
    const helperId = helperText ? `${inputId}-helper` : undefined;
    const describedBy = [errorId, helperId].filter(Boolean).join(' ') || undefined;

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            {label}
          </label>
        )}
        <div className={clsx('relative', icon && 'relative')}>
          <input
            ref={ref}
            id={inputId}
            aria-invalid={!!error}
            aria-describedby={describedBy}
            className={clsx(
              'w-full rounded-md border px-3 py-2 text-sm transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2',
              'bg-white dark:bg-neutral-900 dark:text-neutral-100',
              {
                'border-neutral-300 focus:border-primary-500 dark:border-neutral-700 dark:focus:border-primary-500': !error,
                'border-danger-500 focus:border-danger-500': !!error,
              },
              icon && 'pl-9',
              className
            )}
            {...props}
          />
          {icon && (
            <div className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-500">
              {icon}
            </div>
          )}
        </div>
        {error && (
          <p id={errorId} className="text-sm text-danger-600 dark:text-danger-400" role="alert">
            {error}
          </p>
        )}
        {helperText && !error && (
          <p id={helperId} className="text-sm text-neutral-500 dark:text-neutral-400">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);
