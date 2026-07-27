import { type ReactNode, useEffect } from 'react';
import { useMe } from '../../api/hooks/useAuth';
import { useAuthStore } from '../../auth/store';

export function AuthProvider({ children }: { children: ReactNode }) {
  const setLoading = useAuthStore((s) => s.setLoading);
  const setUser = useAuthStore((s) => s.setUser);
  const tokens = useAuthStore((s) => s.tokens);

  const { isLoading, isError } = useMe({ enabled: Boolean(tokens?.access_token) });

  useEffect(() => {
    setLoading(Boolean(tokens?.access_token) && isLoading);
    if (!tokens?.access_token || isError) {
      setUser(null);
    }
  }, [tokens?.access_token, isLoading, isError, setLoading, setUser]);

  return <>{children}</>;
}
