import { clsx } from 'clsx';
import { type ReactNode } from 'react';
import { type StatusCategory, statusAccentColors } from '../../lib/status';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: ReactNode;
  category?: StatusCategory;
  onClick?: () => void;
}

export function MetricCard({ title, value, subtitle, icon, category = 'neutral', onClick }: MetricCardProps) {
  return (
    <div
      className={clsx(
        'relative overflow-hidden rounded-card border border-neutral-200 bg-white p-5 shadow-card transition-colors dark:border-neutral-800 dark:bg-neutral-900',
        onClick && 'cursor-pointer hover:border-neutral-300 dark:hover:border-neutral-700'
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
      <span className={clsx('absolute left-0 top-0 block h-full w-1', statusAccentColors[category])} />
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">{title}</p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">{value}</p>
          {subtitle && (
            <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className="metric-icon flex h-10 w-10 items-center justify-center rounded-xl text-indigo-500/80 dark:text-indigo-400/90">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}

interface StatusDotProps {
  category: StatusCategory;
  size?: 'sm' | 'md';
}

export function StatusDot({ category, size = 'md' }: StatusDotProps) {
  return (
    <span
      className={clsx(
        'inline-block shrink-0 rounded-full',
        statusAccentColors[category],
        size === 'sm' ? 'h-2 w-2' : 'h-3 w-3'
      )}
      aria-hidden="true"
    />
  );
}
