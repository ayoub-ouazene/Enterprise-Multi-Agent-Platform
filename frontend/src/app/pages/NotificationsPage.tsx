import { useState } from 'react';
import { Info, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Skeleton } from '../../components/layout/Skeleton';
import { StatusDot } from '../../components/layout/MetricCard';
import { Button } from '../../components/ui/Button';
import { Alert } from '../../components/ui/Alert';
import { EmptyState } from '../../components/ui/EmptyState';
import {
  useNotifications,
  useMarkNotificationRead,
  useMarkAllNotificationsRead,
} from '../../api/hooks/useNotifications';
import { getNotificationSeverityMeta } from '../../lib/status';
import { relativeTime, groupByDate } from '../../lib/formatters';
import type { NotificationSeverity } from '../../api/types';

const severityIconMap: Record<NotificationSeverity, typeof Info> = {
  info: Info,
  success: CheckCircle,
  warning: AlertTriangle,
  error: XCircle,
};

export function NotificationsPage() {
  const [filter, setFilter] = useState<'all' | 'unread'>('all');
  const isUnread = filter === 'unread' ? true : undefined;

  const { data: notifications, isLoading, error } = useNotifications({ is_read: isUnread, limit: 50 });
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  const groups = notifications ? groupByDate(notifications) : [];

  return (
    <PageContainer>
      <PageHeader title="Notifications" description="Important updates and alerts">
        <Button
          variant="secondary"
          onClick={() => markAllRead.mutate()}
          isLoading={markAllRead.isPending}
          disabled={markAllRead.isPending || !notifications?.some((n) => !n.is_read)}
        >
          Mark All Read
        </Button>
      </PageHeader>

      <div className="mb-4 flex gap-2" role="tablist" aria-label="Notification filters">
        <FilterButton label="All" active={filter === 'all'} onClick={() => setFilter('all')} />
        <FilterButton label="Unread" active={filter === 'unread'} onClick={() => setFilter('unread')} />
      </div>

      {error && (
        <Alert variant="error" title="Failed to load notifications">
          {error instanceof Error ? error.message : 'Please try again later.'}
        </Alert>
      )}

      {isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex gap-4 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-800">
              <Skeleton variant="circle" className="h-8 w-8" />
              <div className="flex-1 space-y-2">
                <Skeleton variant="text" className="w-1/3" />
                <Skeleton variant="text" className="w-full" />
                <Skeleton variant="text" className="w-20" />
              </div>
            </div>
          ))}
        </div>
      ) : notifications && notifications.length > 0 ? (
        <div className="space-y-6">
          {groups.map((group) => (
            <div key={group.label}>
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
                {group.label}
              </h3>
              <div className="space-y-3">
                {group.items.map((notification) => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onMarkRead={() => markRead.mutate(notification.id)}
                    markReadPending={markRead.isPending && markRead.variables === notification.id}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-neutral-200 bg-white p-8 shadow-xs dark:border-neutral-800 dark:bg-neutral-800">
          <EmptyState
            title={filter === 'unread' ? 'No unread notifications' : 'No notifications'}
            description="You are all caught up."
          />
        </div>
      )}
    </PageContainer>
  );
}

function FilterButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
        active
          ? 'bg-neutral-900 text-white dark:bg-primary-600 dark:text-white'
          : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-400 dark:hover:bg-neutral-700'
      }`}
    >
      {label}
    </button>
  );
}

function NotificationItem({
  notification,
  onMarkRead,
  markReadPending,
}: {
  notification: import('../../api/types').Notification;
  onMarkRead: () => void;
  markReadPending: boolean;
}) {
  const meta = getNotificationSeverityMeta(notification.severity);
  const Icon = severityIconMap[notification.severity] ?? Info;

  return (
    <div
      className={`flex gap-4 rounded-lg border border-neutral-200 bg-white p-4 shadow-xs transition-opacity dark:border-neutral-800 dark:bg-neutral-800 ${
        notification.is_read ? 'opacity-70' : ''
      }`}
    >
      <div className="mt-0.5 shrink-0">
        <div className={`flex h-8 w-8 items-center justify-center rounded-full ${meta.category === 'failed' ? 'bg-danger-100 text-danger-600 dark:bg-danger-900 dark:text-danger-300' : meta.category === 'attention' ? 'bg-warning-100 text-warning-600 dark:bg-warning-900 dark:text-warning-300' : meta.category === 'success' ? 'bg-success-100 text-success-600 dark:bg-success-900 dark:text-success-300' : 'bg-info-100 text-info-600 dark:bg-info-900 dark:text-info-300'}`}>
          <Icon size={16} aria-hidden="true" />
        </div>
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
              {notification.title}
            </p>
            <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">
              {notification.message}
            </p>
          </div>
        </div>
        <div className="mt-2 flex items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400">
          <span>{relativeTime(notification.created_at)}</span>
          {notification.action_required && (
            <span className="inline-flex items-center gap-1 font-semibold text-danger-600 dark:text-danger-400">
              <StatusDot category="attention" size="sm" />
              Action required
            </span>
          )}
          {!notification.is_read && (!notification.action_required) && (
            <button
              onClick={onMarkRead}
              disabled={markReadPending}
              className="text-primary-600 hover:underline dark:text-primary-400 disabled:opacity-50"
            >
              {markReadPending ? 'Marking...' : 'Mark read'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
