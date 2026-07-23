import { useState } from 'react';
import { Card, CardContent, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Alert } from '../../components/ui/Alert';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { EmptyState } from '../../components/ui/EmptyState';
import { useNotifications, useMarkNotificationRead, useMarkAllNotificationsRead } from '../../api/hooks/useNotifications';
import type { Notification } from '../../api/types';

export function NotificationsPage() {
  const [filter, setFilter] = useState<'all' | 'unread'>('all');
  const isUnread = filter === 'unread' ? true : undefined;

  const { data: notifications, isLoading, error } = useNotifications({ is_read: isUnread, limit: 50 });
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
        <Button
          variant="secondary"
          onClick={() => markAllRead.mutate()}
          isLoading={markAllRead.isPending}
          disabled={markAllRead.isPending || !notifications?.some((n) => !n.is_read)}
        >
          Mark All Read
        </Button>
      </div>

      <div className="flex gap-2">
        <FilterButton label="All" active={filter === 'all'} onClick={() => setFilter('all')} />
        <FilterButton label="Unread" active={filter === 'unread'} onClick={() => setFilter('unread')} />
      </div>

      {error && (
        <Alert variant="error" title="Failed to load notifications">
          {error instanceof Error ? error.message : 'Please try again later.'}
        </Alert>
      )}

      <Card>
        <CardHeader className="sr-only">Notifications</CardHeader>
        <CardContent>
          {isLoading ? (
            <LoadingSpinner />
          ) : !notifications || notifications.length === 0 ? (
            <EmptyState
              title={filter === 'unread' ? 'No unread notifications' : 'No notifications'}
              description="You are all caught up."
            />
          ) : (
            <ul className="divide-y divide-gray-200">
              {notifications.map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onMarkRead={() => markRead.mutate(notification.id)}
                  markReadPending={markRead.isPending && markRead.variables === notification.id}
                />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function FilterButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <Button variant={active ? 'primary' : 'ghost'} onClick={onClick}>
      {label}
    </Button>
  );
}

function NotificationItem({
  notification,
  onMarkRead,
  markReadPending,
}: {
  notification: Notification;
  onMarkRead: () => void;
  markReadPending: boolean;
}) {
  const severityIcon = {
    info: 'i',
    success: '\u2713',
    warning: '!',
    error: '\u2717',
  }[notification.severity];

  const severityColor: Record<string, string> = {
    info: 'text-blue-600',
    success: 'text-green-600',
    warning: 'text-amber-500',
    error: 'text-red-600',
  };

  return (
    <li className={`flex items-start gap-3 py-4 ${notification.is_read ? 'opacity-70' : ''}`}>
      <span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-bold ${severityColor[notification.severity]}`}>
        {severityIcon}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-sm font-semibold text-gray-900">{notification.title}</p>
            <p className="mt-1 text-sm text-gray-600">{notification.message}</p>
          </div>
          {!notification.is_read && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onMarkRead}
              isLoading={markReadPending}
            >
              Mark read
            </Button>
          )}
        </div>
        <p className="mt-1 text-xs text-gray-400">
          {formatDate(notification.created_at)}
          {notification.action_required && (
            <span className="ml-2 font-medium text-danger-500">Action required</span>
          )}
        </p>
      </div>
    </li>
  );
}

function formatDate(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}
