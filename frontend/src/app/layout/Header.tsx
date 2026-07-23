import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/Button';
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
    <header className="z-30 border-b border-gray-200 bg-white">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            className="md:hidden"
            onClick={onMenuClick}
            aria-label="Open navigation menu"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </Button>

          <a href="/app" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600 text-white font-bold text-sm">
              EM
            </div>
            <span className="hidden text-lg font-semibold text-gray-900 sm:inline">
              Enterprise
            </span>
          </a>
        </div>

        <div className="flex items-center gap-2">
          {user && (
            <>
              <NotificationBell />

              <div className="relative group">
                <Button variant="ghost" size="sm" className="gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-primary-700 text-xs font-bold">
                    {user.email.charAt(0).toUpperCase()}
                  </div>
                  <span className="hidden text-sm text-gray-700 sm:inline">
                    {user.email}
                  </span>
                </Button>

                <div className="absolute right-0 top-full mt-1 hidden w-48 rounded-md border border-gray-200 bg-white py-1 shadow-lg group-focus-within:block group-hover:block">
                  <button
                    onClick={handleLogout}
                    className="flex w-full items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
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
