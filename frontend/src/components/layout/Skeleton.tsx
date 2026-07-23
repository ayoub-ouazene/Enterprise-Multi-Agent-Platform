import { clsx } from 'clsx';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'rect' | 'circle';
  lines?: number;
}

export function Skeleton({ className, variant = 'rect', lines = 1 }: SkeletonProps) {
  if (variant === 'text') {
    return (
      <div className="flex flex-col gap-2 w-full">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={clsx(
              'h-4 animate-pulse rounded bg-neutral-200 dark:bg-neutral-700',
              i === lines - 1 ? 'w-3/4' : 'w-full',
              className
            )}
          />
        ))}
      </div>
    );
  }

  if (variant === 'circle') {
    return (
      <div
        className={clsx(
          'h-10 w-10 animate-pulse rounded-full bg-neutral-200 dark:bg-neutral-700',
          className
        )}
      />
    );
  }

  return (
    <div
      className={clsx(
        'animate-pulse rounded bg-neutral-200 dark:bg-neutral-700',
        className
      )}
    />
  );
}

export function MetricCardSkeleton() {
  return (
    <div className="relative overflow-hidden rounded-lg border border-neutral-200 bg-white p-4 shadow-xs dark:border-neutral-800 dark:bg-neutral-800">
      <span className="absolute left-0 top-0 block h-full w-1 bg-neutral-300 dark:bg-neutral-600" />
      <Skeleton variant="text" lines={1} className="w-24" />
      <Skeleton variant="rect" className="mt-3 h-8 w-16" />
      <Skeleton variant="text" className="mt-2 w-20" />
    </div>
  );
}
