import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import {
  ChevronDown,
  ChevronsLeft,
  ChevronsRight,
  Hand,
  LogOut,
  Menu,
} from 'lucide-react';
import { ThemeToggle } from '../../components/ui/ThemeToggle';
import { ConnectionStatus } from '../../components/realtime/ConnectionStatus';
import { NotificationBell } from '../../notifications/components/NotificationBell';
import { BrandMark } from '../../components/public/BrandMark';
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
  new: 'New request', profile: 'Profile',
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
    <header className="z-header relative isolate shrink-0">
      {/* Top decorative strip */}
      <div className="h-[3px] w-full bg-gradient-to-r from-violet-500 via-primary-500 to-cyan-500" aria-hidden="true" />

      {/* Glass bar */}
      <div className="relative border-b border-white/15 bg-slate-900/80 backdrop-blur-2xl dark:border-white/10 dark:bg-slate-950/85">
        {/* Subtle inner glow */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
          <div className="absolute -top-16 left-1/4 h-24 w-96 rounded-full bg-primary-500/8 blur-3xl" />
          <div className="absolute -top-12 right-1/4 h-20 w-72 rounded-full bg-violet-500/6 blur-3xl" />
        </div>

        <div className="relative flex h-[3.75rem] items-center gap-3 px-3 sm:px-5 lg:px-6">
          { /* Mobile hamburger */}
          <button
            onClick={onMenuClick}
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl text-white transition hover:bg-white/10 md:hidden"
            aria-label="Open navigation menu"
          >
            <Menu size={20} />
          </button>

          { /* Orchestra Logo */}
          <Link
            to="/app"
            className="group flex shrink-0 items-center gap-3 rounded-xl px-1.5 py-1.5 transition-colors hover:bg-white/10"
            aria-label="Orchestra home"
          >
            <BrandMark />
          </Link>

          { /* Sidebar toggle */}
          <button
            onClick={onSidebarToggle}
            className="ml-1 hidden h-9 w-9 items-center justify-center rounded-lg text-white/70 transition hover:bg-white/10 hover:text-white md:inline-flex"
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-pressed={sidebarCollapsed}
          >
            {sidebarCollapsed ? <ChevronsRight size={18} /> : <ChevronsLeft size={18} />}
          </button>

          { /* Breadcrumb + Title */}
          <div className="hidden min-w-0 flex-1 items-center gap-2 overflow-hidden pl-3 md:flex">
            <div className="h-6 w-px bg-white/20" aria-hidden="true" />
            <div className="min-w-0 pl-2">
              <nav aria-label="Breadcrumb">
                <ol className="flex items-center gap-1 text-[11px] font-medium text-white/70">
                  {crumbs.slice(0, -1).map((crumb) => (
                    <li key={crumb.href} className="flex items-center gap-1">
                      <Link to={crumb.href} className="capitalize transition hover:text-primary-300">
                        {crumb.label}
                      </Link>
                      <span className="text-white/40" aria-hidden="true">/</span>
                    </li>
                  ))}
                </ol>
              </nav>
              <p className="truncate text-sm font-semibold capitalize leading-tight text-neutral-950">
                {pageTitle}
              </p>
            </div>
          </div>

          { /* Right actions */}
          <div className="ml-auto flex shrink-0 items-center gap-0.5 sm:gap-1">
            <ConnectionStatus />

            {actions.length > 0 && (
              <Link
                to="/app/human-actions"
                className="relative hidden h-9 items-center gap-1.5 rounded-lg px-2.5 text-sm text-neutral-800 transition hover:bg-white/10 hover:text-white sm:flex"
                aria-label={`${actions.length} pending human actions`}
              >
                <Hand size={17} />
                <span className="rounded-full bg-amber-500/20 px-1.5 text-[10px] font-bold text-amber-300 ring-1 ring-amber-500/30">
                  {actions.length > 99 ? '99+' : actions.length}
                </span>
              </Link>
            )}

            <NotificationBell />
            <ThemeToggle />

            {user && (
              <div className="relative ml-1" ref={menuRef}>
                <button
                  onClick={() => setMenuOpen((v) => !v)}
                  className="group/profile flex h-10 items-center gap-2 rounded-xl border border-white/15 bg-white/8 px-2 py-1 text-left transition hover:border-white/25 hover:bg-white/12"
                  aria-haspopup="menu"
                  aria-expanded={menuOpen}
                >
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-primary-500 to-violet-600 text-[11px] font-bold text-white shadow-md shadow-primary-600/30">
                    {user.email.charAt(0).toUpperCase()}
                  </span>
                  <span className="hidden max-w-32 flex-col leading-none lg:flex">
                    <span className="truncate text-[11px] font-semibold text-neutral-900">
                      {user.email}
                    </span>
                    <span className="truncate text-[10px] text-neutral-700">
                      {department?.name ?? roleLabel(user)}
                    </span>
                  </span>
                  <ChevronDown
                    size={13}
                    className={`hidden text-white/50 transition-transform lg:block ${menuOpen ? 'rotate-180' : ''}`}
                  />
                </button>

                <AnimatePresence>
                  {menuOpen && (
                    <motion.div
                      role="menu"
                      initial={reducedMotion ? false : { opacity: 0, y: -6, scale: 0.97 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -6, scale: 0.97 }}
                      transition={{ duration: reducedMotion ? 0 : duration.fast, ease: easing.easeOut }}
                      className="absolute right-0 top-full z-dropdown mt-2 w-60 overflow-hidden rounded-xl border border-white/15 bg-slate-900/95 shadow-2xl backdrop-blur-2xl"
                    >
                      <div className="border-b border-white/15 px-4 py-3">
                        <p className="text-sm text-neutral-900">{user.email}</p>
                        <p className="text-xs text-neutral-700">
                          {roleLabel(user)}{department ? ` · ${department.name}` : ''}
                        </p>
                      </div>
                      <button
                        role="menuitem"
                        onClick={handleLogout}
                        className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-neutral-700 hover:bg-white/10"
                      >
                        <LogOut size={16} /> Sign out
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
