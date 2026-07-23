import { useNavigate } from 'react-router-dom';
import { useUnreadCount } from '../../api/hooks/useNotifications';

export function NotificationBell() {
  const navigate = useNavigate();
  const { data } = useUnreadCount();
  const count = data?.unread_count ?? 0;

  return (
    <button
      onClick={() => navigate('/app/notifications')}
      className="relative rounded-full p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
      aria-label={`Notifications${count > 0 ? `, ${count} unread` : ''}`}
    >
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
      </svg>
      {count > 0 && (
        <span className="absolute right-1 top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-danger-500 px-1 text-[10px] font-bold text-white">
          {count > 9 ? '9+' : count}
        </span>
      )}
    </button>
  );
}
