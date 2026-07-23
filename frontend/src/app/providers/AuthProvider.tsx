import { type ReactNode, useEffect, useRef } from 'react';
import { useMe } from '../../api/hooks/useAuth';
import { useAuthStore } from '../../auth/store';

export function AuthProvider({ children }: { children: ReactNode }) {
  const initRef = useRef(false);
  const setLoading = useAuthStore((s) => s.setLoading);
  const setUser = useAuthStore((s) => s.setUser);

  const { isLoading, isError } = useMe({ enabled: !initRef.current });

  useEffect(() => {
    if (!initRef.current) {
      initRef.current = true;
    }
  }, []);

  useEffect(() => {
    setLoading(isLoading);
    if (isError) {
      setUser(null);
    }
  }, [isLoading, isError, setLoading, setUser]);

  return <>{children}</>;
}
