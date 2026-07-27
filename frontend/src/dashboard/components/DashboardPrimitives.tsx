import { Component, type ReactNode } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  Activity, AlertCircle, ArrowRight, CheckCircle2, Clock3, CloudOff,
  RefreshCw, ShieldCheck, TriangleAlert,
} from 'lucide-react';
import { clsx } from 'clsx';
import type {
  DashboardActionItem, DashboardActivityItem, DashboardAttentionItem,
  DashboardMetric, DashboardRequestItem,
} from '../../api/types';
import { useSseConnection } from '../../app/providers/SseProvider';
import { PageContainer } from '../../components/layout/PageContainer';
import { Skeleton } from '../../components/layout/Skeleton';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { EmptyState } from '../../components/ui/EmptyState';
import { duration, easing } from '../../motion/tokens';
import { relativeTime } from '../../lib/formatters';

export function DashboardHeader({ eyebrow, title, subtitle, action, status }: { eyebrow: string; title: string; subtitle: string; action: ReactNode; status?: ReactNode }) {
  return <header className="flex flex-col gap-5 border-b border-neutral-200 pb-6 sm:flex-row sm:items-end sm:justify-between dark:border-neutral-800"><div className="min-w-0"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary-600 dark:text-primary-400">{eyebrow}</p><h1 className="mt-2 text-2xl font-bold tracking-tight text-neutral-950 sm:text-3xl dark:text-white">{title}</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-500 dark:text-neutral-400">{subtitle}</p>{status && <div className="mt-3">{status}</div>}</div><div className="shrink-0">{action}</div></header>;
}

export function RealtimeUpdateIndicator({ refreshing = false }: { refreshing?: boolean }) {
  const { connected } = useSseConnection();
  return <span className={clsx('inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-medium', connected ? 'bg-success-50 text-success-700 dark:bg-success-950 dark:text-success-300' : 'bg-warning-50 text-warning-800 dark:bg-warning-950 dark:text-warning-200')} role="status"><span className={clsx('h-2 w-2 rounded-full', connected ? 'bg-success-500' : 'bg-warning-500')} />{refreshing ? 'Refreshing' : connected ? 'Live updates on' : 'Showing last update'}</span>;
}

export function DashboardSection({ title, description, action, children, className }: { title: string; description?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <DashboardSectionBoundary title={title}><section className={className} aria-labelledby={`section-${title.replace(/\s/g, '-').toLowerCase()}`}><div className="mb-4 flex items-start justify-between gap-4"><div><h2 id={`section-${title.replace(/\s/g, '-').toLowerCase()}`} className="text-base font-semibold text-neutral-950 dark:text-white">{title}</h2>{description && <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{description}</p>}</div>{action}</div>{children}</section></DashboardSectionBoundary>;
}

class DashboardSectionBoundary extends Component<
  { children: ReactNode; title: string },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (!this.state.failed) return this.props.children;
    return <section className="rounded-card border border-warning-200 bg-warning-50/60 p-5 dark:border-warning-900 dark:bg-warning-950/30" role="alert"><p className="font-semibold text-warning-900 dark:text-warning-100">{this.props.title} is temporarily unavailable</p><p className="mt-1 text-sm text-warning-700 dark:text-warning-300">Other dashboard sections are still available.</p><Button variant="secondary" className="mt-4" onClick={() => this.setState({ failed: false })}><RefreshCw size={15} className="mr-2" />Retry section</Button></section>;
  }
}

const metricIcon = { active: Activity, actions: TriangleAlert, completed: CheckCircle2, notifications: AlertCircle, review: ShieldCheck, failed: AlertCircle };
export function DashboardMetricGrid({ metrics }: { metrics: DashboardMetric[] }) {
  const reduced = useReducedMotion();
  return <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">{metrics.map((metric, index) => { const Icon = metricIcon[metric.key as keyof typeof metricIcon] ?? Activity; const content = <motion.div initial={reduced ? false : { opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduced ? 0 : duration.normal, delay: reduced ? 0 : index * .035, ease: easing.easeOut }} className="group h-full rounded-card border border-neutral-200 bg-white p-5 shadow-card transition-colors hover:border-primary-200 dark:border-neutral-800 dark:bg-neutral-900 dark:hover:border-primary-800"><div className="flex items-start justify-between gap-4"><div><p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">{metric.label}</p><AnimatePresence mode="popLayout" initial={false}><motion.p key={metric.value} initial={reduced ? false : { opacity: 0 }} animate={{ opacity: 1 }} className="mt-2 text-3xl font-bold tracking-tight text-neutral-950 dark:text-white">{metric.value}</motion.p></AnimatePresence><p className="mt-1 text-xs text-neutral-500">{metric.detail}</p></div><span className={clsx('flex h-10 w-10 items-center justify-center rounded-xl', metric.status === 'danger' ? 'bg-danger-50 text-danger-600 dark:bg-danger-950' : metric.status === 'warning' ? 'bg-warning-50 text-warning-700 dark:bg-warning-950' : metric.status === 'success' ? 'bg-success-50 text-success-600 dark:bg-success-950' : 'bg-primary-50 text-primary-600 dark:bg-primary-950')}><Icon size={19} aria-hidden="true" /></span></div></motion.div>; return metric.href ? <Link key={metric.key} to={metric.href} className="rounded-card focus-visible:ring-offset-4" aria-label={`${metric.label}: ${metric.value}. ${metric.detail}`}>{content}</Link> : <div key={metric.key}>{content}</div>; })}</div>;
}

export function AttentionQueue({ items, emptyMessage, viewAll = '/app/human-actions' }: { items: DashboardAttentionItem[]; emptyMessage: string; viewAll?: string }) {
  if (!items.length) return <div className="rounded-card border border-success-200 bg-success-50/70 p-5 dark:border-success-900 dark:bg-success-950/30"><div className="flex gap-3"><CheckCircle2 className="mt-0.5 text-success-600" size={20} /><div><p className="font-medium text-success-900 dark:text-success-100">Nothing urgent</p><p className="mt-1 text-sm text-success-700 dark:text-success-300">{emptyMessage}</p></div></div></div>;
  return <div className="overflow-hidden rounded-card border border-neutral-200 bg-white shadow-card dark:border-neutral-800 dark:bg-neutral-900"><ul className="divide-y divide-neutral-100 dark:divide-neutral-800">{items.map((item) => <li key={item.id} className="p-4 sm:p-5"><div className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-x-3 sm:grid-cols-[auto_minmax(0,1fr)_auto]"><span className={clsx('mt-1 h-2.5 w-2.5 shrink-0 rounded-full ring-4', item.severity === 'error' ? 'bg-danger-500 ring-danger-50 dark:ring-danger-950' : 'bg-warning-500 ring-warning-50 dark:ring-warning-950')} /><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><p className="font-medium text-neutral-950 dark:text-white">{item.title}</p><Badge variant={item.severity === 'error' ? 'danger' : 'warning'}>{item.severity === 'error' ? 'High priority' : 'Action needed'}</Badge></div><p className="mt-1 text-sm leading-5 text-neutral-500 dark:text-neutral-400">{item.explanation}</p><p className="mt-2 text-xs text-neutral-400">{item.due_at ? `Due ${relativeTime(item.due_at)}` : item.occurred_at ? relativeTime(item.occurred_at) : 'Current readiness item'}</p></div><Link to={item.action_url} className="col-start-2 mt-3 inline-flex items-center gap-1 text-sm font-semibold text-primary-600 hover:text-primary-700 sm:col-start-3 sm:row-start-1 sm:mt-0">{item.action_label}<ArrowRight size={14} /></Link></div></li>)}</ul>{items.length >= 4 && <div className="border-t border-neutral-100 px-5 py-3 text-right dark:border-neutral-800"><Link to={viewAll} className="text-sm font-semibold text-primary-600">View all</Link></div>}</div>;
}

export function RequestList({ items, emptyTitle, emptyAction = true }: { items: DashboardRequestItem[]; emptyTitle: string; emptyAction?: boolean }) {
  if (!items.length) return <EmptyState title={emptyTitle} description="New work will appear here as soon as it is available." action={emptyAction ? <Link to="/app/requests/new" className="font-semibold text-primary-600">Create a request</Link> : undefined} />;
  return <div className="overflow-hidden rounded-card border border-neutral-200 bg-white shadow-card dark:border-neutral-800 dark:bg-neutral-900"><ul className="divide-y divide-neutral-100 dark:divide-neutral-800">{items.map((item) => <li key={item.id}><Link to={`/app/requests/${item.id}`} className="group flex items-center gap-3 p-4 hover:bg-neutral-50 dark:hover:bg-neutral-800/50"><span className={clsx('h-2 w-2 shrink-0 rounded-full', item.action_required ? 'bg-warning-500' : 'bg-primary-500')} /><div className="min-w-0 flex-1"><div className="flex items-center gap-2"><p className="truncate text-sm font-medium text-neutral-950 dark:text-white">{item.title}</p>{item.action_required && <Badge variant="warning">Your action</Badge>}</div><p className="mt-1 truncate text-xs text-neutral-500">{item.owner_department ?? 'Routing'} · {item.current_stage.replace(/_/g, ' ')} · Updated {relativeTime(item.updated_at)}</p></div><ArrowRight size={16} className="shrink-0 text-neutral-300 group-hover:text-primary-500" /></Link></li>)}</ul></div>;
}

export function PendingActions({ items }: { items: DashboardActionItem[] }) {
  if (!items.length) return <EmptyState title="No pending actions" description="You do not have any assigned actions right now." />;
  return <div className="grid gap-3">{items.map((item) => <Link key={item.id} to={`/app/human-actions/${item.id}`} className="flex items-center gap-3 rounded-xl border border-neutral-200 bg-white p-4 hover:border-primary-300 dark:border-neutral-800 dark:bg-neutral-900"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-warning-50 text-warning-700 dark:bg-warning-950"><Clock3 size={17} /></span><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-neutral-950 dark:text-white">{item.title}</p><p className="mt-1 text-xs text-neutral-500">{item.action_type.replace(/_/g, ' ')}{item.due_at ? ` · Due ${relativeTime(item.due_at)}` : ''}</p></div><ArrowRight size={15} className="text-neutral-400" /></Link>)}</div>;
}

export function ActivityFeed({ items }: { items: DashboardActivityItem[] }) {
  if (!items.length) return <EmptyState title="No recent activity" description="Meaningful updates will appear here." />;
  return <ol className="relative space-y-5 before:absolute before:bottom-2 before:left-[7px] before:top-2 before:w-px before:bg-neutral-200 dark:before:bg-neutral-800">{items.map((item) => <li key={item.id} className="relative flex gap-3"><span className="relative z-10 mt-1.5 h-3.5 w-3.5 shrink-0 rounded-full border-[3px] border-white bg-primary-500 ring-1 ring-neutral-200 dark:border-neutral-900 dark:ring-neutral-700" /><div className="min-w-0"><p className="text-sm font-medium text-neutral-900 dark:text-white">{item.title}</p><p className="mt-0.5 line-clamp-2 text-xs leading-5 text-neutral-500">{item.message}</p><p className="mt-1 text-[11px] text-neutral-400">{relativeTime(item.occurred_at)}</p></div></li>)}</ol>;
}

export function QuickActions({ items }: { items: { label: string; description: string; href: string; primary?: boolean }[] }) {
  return <div className="grid gap-3 sm:grid-cols-2">{items.map((item) => <Link key={item.href} to={item.href} className={clsx('group rounded-xl border p-4 transition-colors', item.primary ? 'border-primary-200 bg-primary-50 dark:border-primary-900 dark:bg-primary-950/40' : 'border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900')}><p className={clsx('text-sm font-semibold', item.primary ? 'text-primary-800 dark:text-primary-200' : 'text-neutral-900 dark:text-white')}>{item.label}<ArrowRight size={14} className="ml-1 inline transition-transform group-hover:translate-x-0.5" /></p><p className="mt-1 text-xs leading-5 text-neutral-500">{item.description}</p></Link>)}</div>;
}

export function DashboardSkeleton() {
  return <PageContainer><div aria-label="Loading dashboard" role="status"><Skeleton className="h-4 w-28" /><Skeleton className="mt-3 h-9 w-80 max-w-full" /><Skeleton className="mt-3 h-4 w-[32rem] max-w-full" /><div className="mt-8 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-32 rounded-card" />)}</div><div className="mt-8 grid gap-6 lg:grid-cols-[1.35fr_.65fr]"><Skeleton className="h-80 rounded-card" /><Skeleton className="h-80 rounded-card" /></div></div></PageContainer>;
}

export function FullDashboardError({ onRetry }: { onRetry: () => void }) {
  return <PageContainer><div className="mx-auto max-w-lg rounded-card border border-danger-200 bg-white p-8 text-center shadow-card dark:border-danger-900 dark:bg-neutral-900"><CloudOff className="mx-auto text-danger-500" size={34} /><h1 className="mt-4 text-xl font-semibold">Dashboard unavailable</h1><p className="mt-2 text-sm text-neutral-500">Your workspace is still available. We could not load the latest summary.</p><Button onClick={onRetry} className="mt-5"><RefreshCw size={16} className="mr-2" />Try again</Button></div></PageContainer>;
}

export class DashboardErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <FullDashboardError onRetry={() => this.setState({ failed: false })} /> : this.props.children; }
}
