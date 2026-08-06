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
import { NoiseTexture } from '../../components/backgrounds/NoiseTexture';

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
    <div className="relative flex h-dvh min-h-0 flex-col bg-slate-950">
      <SkipToContent />
      <Header
        onMenuClick={() => setSidebarOpen(true)}
        sidebarCollapsed={collapsed}
        onSidebarToggle={toggleCollapsed}
      />
      <div className="relative flex min-h-0 flex-1 overflow-hidden">
        {/* Subtle atmospheric background */}
        <div className="pointer-events-none absolute inset-0 bg-slate-950" aria-hidden="true" />
        <div className="pointer-events-none absolute inset-0 gradient-orb-bg opacity-40" aria-hidden="true" />
        <div className="pointer-events-none absolute inset-0 dot-grid opacity-[0.07]" aria-hidden="true" />
        <NoiseTexture opacity={0.02} />

        <aside
          className="relative z-[1] hidden shrink-0 overflow-x-hidden overflow-y-auto border-r border-white/8 bg-slate-900/90 transition-[width] duration-panel ease-productive md:block"
          style={{ width: collapsed ? 'var(--sidebar-compact)' : 'var(--sidebar-wide)' }}
          aria-label="Desktop navigation"
        >
          <div className="h-full py-4">
            <Sidebar user={user} collapsed={collapsed} />
          </div>
        </aside>

        <MobileNav isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} user={user} />

        <main id="main-content" className="relative z-[1] min-w-0 flex-1 overflow-y-auto scroll-smooth" tabIndex={-1}>
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
