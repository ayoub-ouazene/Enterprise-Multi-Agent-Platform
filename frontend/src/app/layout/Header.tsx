import { useNavigate } from 'react-router-dom';
import { Menu } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { ThemeToggle } from '../../components/ui/ThemeToggle';
import { ConnectionStatus } from '../../components/realtime/ConnectionStatus';
import { NotificationBell } from '../../notifications/components/NotificationBell';
import { useAuthContext } from '../../auth/hooks/useAuthContext';

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const { user, logout } = useAuthContext();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="z-30 border-b border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            className="text-neutral-500 md:hidden"
            onClick={onMenuClick}
            aria-label="Open navigation menu"
          >
            <Menu size={20} aria-hidden="true" />
          </Button>

          <a href="/app" className="flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 rounded-sm">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600 text-white font-bold text-sm">
              EM
            </div>
            <span className="hidden text-lg font-semibold text-neutral-900 dark:text-neutral-100 sm:inline">
              TellUS AI
            </span>
          </a>
        </div>

        <div className="flex items-center gap-1">
          {user && (
            <>
              <ConnectionStatus />
              <div className="mx-1 hidden h-5 w-px bg-neutral-200 dark:bg-neutral-800 sm:block" />
              <NotificationBell />
              <ThemeToggle />

              <div className="relative ml-1">
                <button
                  className="flex items-center gap-2 rounded-md p-1.5 text-sm text-neutral-700 hover:bg-neutral-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:text-neutral-300 dark:hover:bg-neutral-800"
                  aria-haspopup="menu"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-primary-700 text-xs font-bold dark:bg-primary-900 dark:text-primary-300">
                    {user.email.charAt(0).toUpperCase()}
                  </div>
                  <span className="hidden max-w-[140px] truncate text-sm text-neutral-700 dark:text-neutral-300 sm:inline">
                    {user.email}
                  </span>
                </button>

                <div className="absolute right-0 top-full mt-1 hidden w-48 rounded-lg border border-neutral-200 bg-white py-1 shadow-sm group-[]:focus-within:block group-[]:hover:block dark:border-neutral-800 dark:bg-neutral-900">
                  <button
                    onClick={handleLogout}
                    className="flex w-full items-center px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 dark:text-neutral-300 dark:hover:bg-neutral-800"
                  >
                    Sign out
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
