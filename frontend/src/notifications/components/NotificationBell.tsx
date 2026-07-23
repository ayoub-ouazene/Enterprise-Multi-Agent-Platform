import { useNavigate } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { useUnreadCount } from '../../api/hooks/useNotifications';

export function NotificationBell() {
  const navigate = useNavigate();
  const { data } = useUnreadCount();
  const count = data?.unread_count ?? 0;

  return (
    <button
      onClick={() => navigate('/app/notifications')}
      className="relative rounded-full p-2 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-neutral-200"
      aria-label={`Notifications${count > 0 ? `, ${count} unread` : ''}`}
    >
      <Bell size={20} aria-hidden="true" />
      {count > 0 && (
        <span className="absolute right-1 top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-danger-500 px-1 text-[10px] font-bold text-white">
          {count > 9 ? '9+' : count}
        </span>
      )}
    </button>
  );
}
