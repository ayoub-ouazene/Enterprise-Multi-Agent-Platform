export function TableSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      <div className="h-8 animate-pulse rounded bg-neutral-200 dark:bg-neutral-800" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-10 animate-pulse rounded bg-neutral-200 dark:bg-neutral-800" />
      ))}
    </div>
  );
}
