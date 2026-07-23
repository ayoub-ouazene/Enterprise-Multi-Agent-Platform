import { createContext, type ReactNode, useContext, useEffect, useRef, useState } from 'react';
import { useAuthStore } from '../../auth/store';
import type { QueryClient } from '@tanstack/react-query';

type SseConnection = {
  connect: (url: string) => void;
  disconnect: () => void;
  connected: boolean;
};

const SseContext = createContext<SseConnection>({
  connect: () => {},
  disconnect: () => {},
  connected: false,
});

export function useSseConnection() {
  return useContext(SseContext);
}

interface SseProviderProps {
  children: ReactNode;
  queryClient?: QueryClient;
}

export function SseProvider({ children, queryClient }: SseProviderProps) {
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tokens = useAuthStore((s) => s.tokens);

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
      setConnected(false);
    }
  };

  const connect = (url: string) => {
    disconnect();
    if (!tokens?.access_token) return;

    const fullUrl = `${url}?token=${encodeURIComponent(tokens.access_token)}`;
    const es = new EventSource(fullUrl);
    esRef.current = es;

    es.onopen = () => {
      setConnected(true);
    };

    es.onmessage = (event) => {
      if (queryClient && event.data) {
        try {
          const data = JSON.parse(event.data);
          const eventType = data?.event_type || data?.type || 'update';
          const entity = data?.entity;

          if (entity === 'notification' || entity === 'notifications') {
            queryClient.invalidateQueries({ queryKey: ['notifications'] });
            queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] });
          }
          if (entity === 'request' || entity === 'requests') {
            queryClient.invalidateQueries({ queryKey: ['requests'] });
            if (data?.request_id) {
              queryClient.invalidateQueries({ queryKey: ['request', data.request_id] });
            }
          }
          if (entity === 'human_action' || entity === 'human_actions') {
            queryClient.invalidateQueries({ queryKey: ['human-actions'] });
          }
          if (eventType === 'import_done') {
            queryClient.invalidateQueries({ queryKey: ['onboarding'] });
          }
        } catch {
          // Non-JSON messages: soft-fail
        }
      }
    };

    es.onerror = () => {
      setConnected(false);
      reconnectTimeoutRef.current = setTimeout(() => {
        if (esRef.current === es) {
          connect(url);
        }
      }, 5000);
    };
  };

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, []);

  useEffect(() => {
    if (!tokens) {
      disconnect();
    }
  }, [tokens]);

  return (
    <SseContext.Provider value={{ connect, disconnect, connected }}>
      {children}
    </SseContext.Provider>
  );
}
