import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { MobileNav } from './MobileNav';
import { useAuthContext } from '../../auth/hooks/useAuthContext';
import { fadeInUp } from '../../motion/tokens';

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user } = useAuthContext();

  return (
    <div className="flex h-screen flex-col bg-neutral-50 dark:bg-neutral-900">
      <SkipToContent />
      <Header onMenuClick={() => setSidebarOpen(true)} />

      <div className="flex flex-1 overflow-hidden">
        {/* Desktop sidebar */}
        <aside className="hidden w-64 flex-shrink-0 overflow-y-auto border-r border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900 md:block">
          <div className="py-4">
            <Sidebar user={user} onNavigate={() => setSidebarOpen(false)} />
          </div>
        </aside>

        {/* Mobile drawer */}
        <MobileNav
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          user={user}
        />

        {/* Main content */}
        <main id="main-content" className="scroll-mt-16 flex-1 overflow-y-auto">
          <PageContentTransition>
            <Outlet />
          </PageContentTransition>
        </main>
      </div>
    </div>
  );
}

function SkipToContent() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:rounded-md focus:bg-primary-600 focus:px-4 focus:py-2 focus:text-white focus:shadow-sm"
    >
      Skip to main content
    </a>
  );
}

function PageContentTransition({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={location.pathname}
        initial={fadeInUp.initial}
        animate={fadeInUp.animate}
        exit={fadeInUp.exit}
        transition={fadeInUp.transition}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
