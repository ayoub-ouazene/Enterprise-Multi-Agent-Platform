import { useEffect } from 'react';
import { RouterProvider } from 'react-router-dom';
import { useAuthStore } from './auth/store';
import { useThemeStore } from './lib/theme-store';
import { queryClient } from './app/providers/QueryProvider';
import { QueryProvider } from './app/providers/QueryProvider';
import { AuthProvider } from './app/providers/AuthProvider';
import { SseProvider } from './app/providers/SseProvider';
import { router } from './app/router';

export default function App() {
  const initTheme = useThemeStore((s) => s.init);
  const initAuth = useAuthStore((s) => s.init);

  useEffect(() => {
    initTheme();
    initAuth?.();
  }, [initTheme, initAuth]);

  return (
    <QueryProvider>
      <AuthProvider>
        <SseProvider queryClient={queryClient}>
          <RouterProvider router={router} />
        </SseProvider>
      </AuthProvider>
    </QueryProvider>
  );
}
