import { AlertTriangle, CheckCircle2, CloudOff, FileQuestion, LockKeyhole, SearchX } from 'lucide-react';
import { Button } from '../ui/Button';
import { Skeleton } from '../layout/Skeleton';

export function PageLoading({ label = 'Loading page' }: { label?: string }) {
  return <div className="mx-auto max-w-7xl space-y-5 p-6" role="status" aria-label={label}><Skeleton className="h-8 w-56" /><Skeleton className="h-4 w-96 max-w-full" /><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><Skeleton className="h-36" /><Skeleton className="h-36" /><Skeleton className="h-36" /></div></div>;
}

export function SectionLoading({ rows = 3 }: { rows?: number }) {
  return <div className="space-y-3" role="status" aria-label="Loading section">{Array.from({ length: rows }, (_, index) => <Skeleton key={index} className="h-12 w-full" />)}</div>;
}

type StateKind = 'empty' | 'error' | 'denied' | 'not-found' | 'session' | 'offline' | 'success';
const icons = { empty: FileQuestion, error: AlertTriangle, denied: LockKeyhole, 'not-found': SearchX, session: LockKeyhole, offline: CloudOff, success: CheckCircle2 };

export function StatePanel({ kind, title, description, actionLabel, onAction }: { kind: StateKind; title: string; description: string; actionLabel?: string; onAction?: () => void }) {
  const Icon = icons[kind];
  return <section className="mx-auto flex max-w-lg flex-col items-center rounded-card border border-neutral-200 bg-white px-6 py-10 text-center shadow-card dark:border-neutral-800 dark:bg-neutral-900" role={kind === 'error' || kind === 'offline' ? 'alert' : 'status'}><span className={kind === 'success' ? 'text-success-600' : kind === 'error' ? 'text-danger-600' : 'text-neutral-400'}><Icon size={36} aria-hidden="true" /></span><h2 className="mt-4 text-lg font-semibold text-neutral-950 dark:text-white">{title}</h2><p className="mt-2 text-sm leading-6 text-neutral-500 dark:text-neutral-400">{description}</p>{actionLabel && onAction && <Button className="mt-5" onClick={onAction}>{actionLabel}</Button>}</section>;
}

export function SuccessConfirmation({ message }: { message: string }) {
  return <div className="flex items-center gap-2 rounded-lg border border-success-200 bg-success-50 px-4 py-3 text-sm text-success-800 dark:border-success-800 dark:bg-success-950/50 dark:text-success-200" role="status"><CheckCircle2 size={18} aria-hidden="true" />{message}</div>;
}
