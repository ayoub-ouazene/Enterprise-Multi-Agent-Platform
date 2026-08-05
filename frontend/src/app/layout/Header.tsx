import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import { ChevronDown, ChevronsLeft, ChevronsRight, Hand, LogOut, Menu } from 'lucide-react';
import { ThemeToggle } from '../../components/ui/ThemeToggle';
import { ConnectionStatus } from '../../components/realtime/ConnectionStatus';
import { NotificationBell } from '../../notifications/components/NotificationBell';
import { useAuthContext } from '../../auth/hooks/useAuthContext';
import { useHumanActions } from '../../api/hooks/useHumanActions';
import { useDepartments } from '../../api/hooks/useDepartments';
import { roleLabel } from './shell-utils';
import { clearSensitiveSession } from './session-cleanup';
import { duration, easing } from '../../motion/tokens';

interface HeaderProps {
  onMenuClick: () => void;
  sidebarCollapsed: boolean;
  onSidebarToggle: () => void;
}

const LABELS: Record<string, string> = {
  app: 'Workspace', overview: 'Dashboard', dashboard: 'Dashboard', assistant: 'Assistant', requests: 'Requests',
  'human-actions': 'Human actions', notifications: 'Notifications', onboarding: 'Onboarding',
  admin: 'Administration', departments: 'Departments', 'self-service': 'My workspace',
  new: 'New request',
};

export function Header({ onMenuClick, sidebarCollapsed, onSidebarToggle }: HeaderProps) {
  const { user, logout } = useAuthContext();
  const navigate = useNavigate();
  const location = useLocation();
  const reducedMotion = useReducedMotion();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const { data: actions = [] } = useHumanActions({ status: 'pending', limit: 100 });
  const { data: departments = [] } = useDepartments();

  useEffect(() => {
    function close(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setMenuOpen(false);
    }
    function escape(event: KeyboardEvent) {
      if (event.key === 'Escape') setMenuOpen(false);
    }
    if (menuOpen) {
      document.addEventListener('mousedown', close);
      document.addEventListener('keydown', escape);
    }
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', escape);
    };
  }, [menuOpen]);

  const handleLogout = () => {
    setMenuOpen(false);
    clearSensitiveSession(logout);
    navigate('/login', { replace: true });
  };

  const crumbs = location.pathname.split('/').filter(Boolean).map((segment, index, all) => ({
    label: LABELS[segment] ?? (segment.length > 20 ? 'Details' : segment.replace(/-/g, ' ')),
    href: `/${all.slice(0, index + 1).join('/')}`,
  })).slice(1);
  const pageTitle = crumbs[crumbs.length - 1]?.label ?? 'Workspace';
  const department = departments.find((item) => item.id === user?.department_id);

  return (
    <header className="z-header relative shrink-0 border-b border-neutral-200/80 bg-white/70 backdrop-blur-xl dark:border-neutral-800/80 dark:bg-neutral-900/70">
      <div className="absolute inset-0 overflow-hidden" aria-hidden="true">
        <div className="absolute -top-8 left-1/4 h-20 w-64 rounded-full bg-primary-400/10 blur-3xl" />
        <div className="absolute -top-4 right-1/3 h-16 w-48 rounded-full bg-violet-400/5 blur-2xl" />
      </div>
      <div className="relative flex h-16 items-center gap-3 px-3 sm:px-5 lg:px-6">
        <button
          onClick={onMenuClick}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-neutral-500 hover:bg-neutral-100 md:hidden dark:hover:bg-neutral-800"
          aria-label="Open navigation menu"
        >
          <Menu size={20} aria-hidden="true" />
        </button>

        <Link to="/app" className="flex shrink-0 items-center gap-2.5 rounded-lg">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-600 text-sm font-bold text-white shadow-sm">T</span>
          <span className="hidden text-base font-semibold tracking-tight text-neutral-950 sm:block dark:text-white">Orchestra</span>
        </Link>

        <button
          onClick={onSidebarToggle}
          className="ml-1 hidden h-9 w-9 items-center justify-center rounded-lg text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 md:inline-flex dark:hover:bg-neutral-800 dark:hover:text-white"
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-pressed={sidebarCollapsed}
        >
          {sidebarCollapsed ? <ChevronsRight size={18} /> : <ChevronsLeft size={18} />}
        </button>

        <div className="hidden min-w-0 flex-1 border-l border-neutral-200 pl-4 md:block dark:border-neutral-800">
          <nav aria-label="Breadcrumb">
            <ol className="flex items-center gap-1 text-[11px] text-neutral-500">
              {crumbs.slice(0, -1).map((crumb) => (
                <li key={crumb.href} className="flex items-center gap-1">
                  <Link to={crumb.href} className="capitalize hover:text-primary-600">{crumb.label}</Link>
                  <span aria-hidden="true">/</span>
                </li>
              ))}
            </ol>
          </nav>
          <p className="truncate text-sm font-semibold capitalize text-neutral-900 dark:text-white">{pageTitle}</p>
        </div>

        <div className="ml-auto flex shrink-0 items-center gap-0.5 sm:gap-1">
          <ConnectionStatus />
          {actions.length > 0 && (
            <Link
              to="/app/human-actions"
              className="relative hidden h-9 items-center gap-1.5 rounded-lg px-2 text-sm text-neutral-600 hover:bg-neutral-100 sm:flex dark:text-neutral-300 dark:hover:bg-neutral-800"
              aria-label={`${actions.length} pending human actions`}
            >
              <Hand size={17} aria-hidden="true" />
              <span className="rounded-full bg-warning-100 px-1.5 text-[10px] font-bold text-warning-800 dark:bg-warning-900 dark:text-warning-200">
                {actions.length > 99 ? '99+' : actions.length}
              </span>
            </Link>
          )}
          <NotificationBell />
          <ThemeToggle />

          {user && (
            <div className="relative ml-0.5" ref={menuRef}>
              <button
                onClick={() => setMenuOpen((value) => !value)}
                className="flex h-10 items-center gap-2 rounded-lg px-1.5 text-left hover:bg-neutral-100 dark:hover:bg-neutral-800"
                aria-haspopup="menu"
                aria-expanded={menuOpen}
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-xs font-bold text-primary-700 dark:bg-primary-950 dark:text-primary-300">
                  {user.email.charAt(0).toUpperCase()}
                </span>
                <span className="hidden max-w-36 lg:block">
                  <span className="block truncate text-xs font-semibold text-neutral-900 dark:text-white">{user.email}</span>
                  <span className="block truncate text-[10px] text-neutral-500">{department?.name ?? roleLabel(user)}</span>
                </span>
                <ChevronDown size={14} className="hidden text-neutral-400 lg:block" aria-hidden="true" />
              </button>

              <AnimatePresence>
                {menuOpen && (
                  <motion.div
                    role="menu"
                    initial={reducedMotion ? false : { opacity: 0, y: -4, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -4, scale: 0.98 }}
                    transition={{ duration: reducedMotion ? 0 : duration.fast, ease: easing.easeOut }}
                    className="absolute right-0 top-full z-dropdown mt-2 w-64 overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-overlay dark:border-neutral-700 dark:bg-neutral-900"
                  >
                    <div className="border-b border-neutral-100 px-4 py-3 dark:border-neutral-800">
                      <p className="truncate text-sm font-semibold text-neutral-900 dark:text-white">{user.email}</p>
                      <p className="mt-0.5 text-xs text-neutral-500">{roleLabel(user)}{department ? ` · ${department.name}` : ''}</p>
                    </div>
                    <button role="menuitem" onClick={handleLogout} className="flex w-full items-center gap-2.5 px-4 py-3 text-sm text-neutral-700 hover:bg-neutral-50 dark:text-neutral-300 dark:hover:bg-neutral-800">
                      <LogOut size={16} aria-hidden="true" /> Sign out
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
