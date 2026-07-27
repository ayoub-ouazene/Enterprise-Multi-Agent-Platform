import { useEffect, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Outlet, useLocation } from 'react-router-dom';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { MobileNav } from './MobileNav';
import { useAuthContext } from '../../auth/hooks/useAuthContext';
import { API_BASE } from '../../api/client';
import { useSseConnection } from '../providers/SseProvider';
import { duration, easing } from '../../motion/tokens';
import { getInitialSidebarCollapsed, persistSidebarCollapsed } from './shell-utils';

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(getInitialSidebarCollapsed);
  const { user } = useAuthContext();
  const { connect, disconnect } = useSseConnection();
  const location = useLocation();
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    connect(`${API_BASE}/notifications/stream`);
    return disconnect;
  }, [connect, disconnect]);

  const toggleCollapsed = () => {
    setCollapsed((value) => {
      persistSidebarCollapsed(!value);
      return !value;
    });
  };

  return (
    <div className="flex h-dvh min-h-0 flex-col bg-neutral-50 dark:bg-neutral-950">
      <SkipToContent />
      <Header
        onMenuClick={() => setSidebarOpen(true)}
        sidebarCollapsed={collapsed}
        onSidebarToggle={toggleCollapsed}
      />
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <aside
          className="hidden shrink-0 overflow-x-hidden overflow-y-auto border-r border-neutral-200 bg-white transition-[width] duration-panel ease-productive dark:border-neutral-800 dark:bg-neutral-900 md:block"
          style={{ width: collapsed ? 'var(--sidebar-compact)' : 'var(--sidebar-wide)' }}
          aria-label="Desktop navigation"
        >
          <div className="h-full py-4">
            <Sidebar user={user} collapsed={collapsed} />
          </div>
        </aside>

        <MobileNav isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} user={user} />

        <main id="main-content" className="min-w-0 flex-1 overflow-y-auto scroll-smooth" tabIndex={-1}>
          <motion.div
            key={location.pathname}
            initial={reducedMotion ? false : { opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reducedMotion ? 0 : duration.page, ease: easing.easeOut }}
          >
            <Outlet />
          </motion.div>
        </main>
      </div>
    </div>
  );
}

function SkipToContent() {
  return <a href="#main-content" className="skip-link">Skip to main content</a>;
}
