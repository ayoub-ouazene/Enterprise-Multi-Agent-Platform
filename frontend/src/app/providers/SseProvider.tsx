import { createContext, type ReactNode, useContext, useEffect, useRef, useState } from 'react';
import { useAuthStore } from '../../auth/store';

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

export function SseProvider({ children }: { children: ReactNode }) {
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

    es.onerror = () => {
      setConnected(false);
      // Auto-reconnect with backoff
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
