import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { MobileNav } from './MobileNav';
import { useAuthContext } from '../../auth/hooks/useAuthContext';

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user } = useAuthContext();

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      <Header onMenuClick={() => setSidebarOpen(true)} />

      <div className="flex flex-1 overflow-hidden">
        {/* Desktop sidebar */}
        <aside className="hidden w-64 flex-shrink-0 overflow-y-auto border-r border-gray-200 bg-white md:block">
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
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
