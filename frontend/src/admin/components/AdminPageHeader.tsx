import type { ReactNode } from 'react';

export function AdminPageHeader({
  eyebrow = 'Company administration',
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary-700 dark:text-primary-300">{eyebrow}</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-neutral-950 dark:text-white">{title}</h1>
        <p className="mt-1 max-w-3xl text-sm text-neutral-600 dark:text-neutral-400">{description}</p>
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </header>
  );
}
