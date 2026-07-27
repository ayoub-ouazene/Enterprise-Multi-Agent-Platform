import { type ReactNode } from 'react';
import { clsx } from 'clsx';

interface PageContainerProps {
  children: ReactNode;
  className?: string;
  fullWidth?: boolean;
}

export function PageContainer({ children, className, fullWidth }: PageContainerProps) {
  return (
    <div className={clsx('mx-auto px-4 py-6 sm:px-6 lg:px-8', fullWidth ? 'max-w-none' : 'max-w-7xl', className)}>
      {children}
    </div>
  );
}

interface PageHeaderProps {
  title: string;
  description?: string;
  children?: ReactNode;
  eyebrow?: string;
}

export function PageHeader({ title, description, children, eyebrow }: PageHeaderProps) {
  return (
    <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        {eyebrow && <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-primary-600 dark:text-primary-400">{eyebrow}</p>}
        <h1 className="text-2xl font-bold tracking-tight text-neutral-950 dark:text-white sm:text-[1.75rem]">
          {title}
        </h1>
        {description && (
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            {description}
          </p>
        )}
      </div>
      {children && <div className="flex shrink-0 flex-wrap items-center gap-2">{children}</div>}
    </header>
  );
}

interface SectionProps {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Section({ title, description, actions, children, className }: SectionProps) {
  return (
    <section className={clsx('rounded-card border border-neutral-200 bg-white shadow-card dark:border-neutral-800 dark:bg-neutral-900', className)}>
      {title && (
        <div className="flex items-start justify-between gap-4 border-b border-neutral-200 px-5 py-4 dark:border-neutral-800">
          <div><h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{title}</h2>{description && <p className="mt-1 text-sm text-neutral-500">{description}</p>}</div>
          {actions}
        </div>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function ResponsiveGrid({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx('grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3', className)}>{children}</div>;
}

export function MetricGrid({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx('grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4', className)}>{children}</div>;
}

export function SplitLayout({ primary, secondary, className }: { primary: ReactNode; secondary: ReactNode; className?: string }) {
  return <div className={clsx('grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]', className)}><div className="min-w-0">{primary}</div><aside className="min-w-0">{secondary}</aside></div>;
}

export function FilterBar({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx('flex flex-col gap-3 rounded-card border border-neutral-200 bg-white p-4 sm:flex-row sm:items-center dark:border-neutral-800 dark:bg-neutral-900', className)}>{children}</div>;
}
