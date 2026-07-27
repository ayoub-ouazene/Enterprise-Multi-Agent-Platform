import { createContext, type ReactNode, useCallback, useContext, useEffect, useRef, useState } from 'react';
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
  const seenEventIds = useRef<string[]>([]);
  const tokens = useAuthStore((s) => s.tokens);

  const disconnect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
      setConnected(false);
    }
  }, []);

  const connect = useCallback((url: string) => {
    disconnect();
    if (!tokens?.access_token) return;

    const separator = url.includes('?') ? '&' : '?';
    const fullUrl = `${url}${separator}token=${encodeURIComponent(tokens.access_token)}`;
    const es = new EventSource(fullUrl);
    esRef.current = es;

    es.onopen = () => {
      setConnected(true);
    };

    const handleMessage = (event: MessageEvent) => {
      if (queryClient && event.data) {
        try {
          const data = JSON.parse(event.data);
          const eventType = data?.event_type || data?.type || 'update';
          const entity = data?.entity;
          const eventId = event.lastEventId || data?.id || data?.event_id;
          if (eventId && seenEventIds.current.includes(String(eventId))) return;
          if (eventId) {
            seenEventIds.current = [...seenEventIds.current.slice(-99), String(eventId)];
          }

          if (
            event.type === 'notification'
            || entity === 'notification'
            || entity === 'notifications'
          ) {
            queryClient.invalidateQueries({ queryKey: ['notifications'] });
            queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
            if (
              data?.notification_type === 'human_action_required'
              || data?.notification_type === 'approval_required'
              || data?.notification_type === 'information_required'
            ) {
              queryClient.invalidateQueries({ queryKey: ['human-actions'] });
            }
          }
          if (entity === 'request' || entity === 'requests') {
            invalidateCachedRequestLists(queryClient, data?.request_id);
            if (data?.request_id) {
              queryClient.invalidateQueries({ queryKey: ['request', data.request_id] });
            }
            invalidateDepartmentQueries(queryClient);
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
          }
          if (event.type === 'workflow_event' || data?.request_id) {
            const requestId = data?.request_id;
            if (requestId) {
              queryClient.invalidateQueries({ queryKey: ['request', requestId] });
              queryClient.invalidateQueries({ queryKey: ['workflow-events', requestId] });
              queryClient.invalidateQueries({ queryKey: ['human-actions'] });
            }
            invalidateCachedRequestLists(queryClient, requestId);
            invalidateDepartmentQueries(queryClient);
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
          }
          if (entity === 'human_action' || entity === 'human_actions') {
            queryClient.invalidateQueries({ queryKey: ['human-actions'] });
            if (data?.action_id) {
              queryClient.invalidateQueries({ queryKey: ['human-action', data.action_id] });
            }
            if (data?.request_id) {
              queryClient.invalidateQueries({ queryKey: ['request', data.request_id] });
            }
            invalidateDepartmentQueries(queryClient);
            queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
          }
          if (eventType === 'import_done') {
            queryClient.invalidateQueries({ queryKey: ['onboarding'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
          }
          const adminQuery = adminEntityQueryKey(entity);
          if (adminQuery) {
            queryClient.invalidateQueries({ queryKey: adminQuery });
            queryClient.invalidateQueries({ queryKey: ['admin', 'summary'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
          }
        } catch {
          // Non-JSON messages: soft-fail
        }
      }
    };
    es.onmessage = handleMessage;
    es.addEventListener('notification', handleMessage);
    es.addEventListener('workflow_event', handleMessage);

    es.onerror = () => {
      setConnected(false);
    };
  }, [disconnect, queryClient, tokens?.access_token]);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  useEffect(() => {
    if (!tokens) {
      disconnect();
    }
  }, [tokens, disconnect]);

  return (
    <SseContext.Provider value={{ connect, disconnect, connected }}>
      {children}
    </SseContext.Provider>
  );
}

function adminEntityQueryKey(entity: unknown): readonly string[] | null {
  const keys: Record<string, readonly string[]> = {
    employee: ['admin', 'employees'],
    department: ['admin', 'departments'],
    manager_assignment: ['onboarding', 'manager-coverage'],
    asset: ['admin', 'assets'],
    software: ['admin', 'software-catalog'],
    budget: ['admin', 'budgets'],
    supplier: ['admin', 'suppliers'],
    holiday: ['admin', 'holidays'],
    staffing_rule: ['admin', 'staffing-rules'],
    knowledge_document: ['admin', 'policy-readiness'],
  };
  return typeof entity === 'string' ? keys[entity] ?? null : null;
}

function invalidateCachedRequestLists(queryClient: QueryClient, requestId?: string) {
  queryClient.invalidateQueries({
    predicate: (query) => {
      if (query.queryKey[0] !== 'requests') return false;
      if (!requestId) return true;
      const data = query.state.data;
      return Array.isArray(data) && data.some(
        (request) => typeof request === 'object' && request !== null && 'id' in request && request.id === requestId,
      );
    },
  });
}

function invalidateDepartmentQueries(queryClient: QueryClient) {
  const deptKeys = [
    'departments',
    'department-stats',
    'department-requests',
    'department-actions',
    'department-readiness',
    'department-activity',
    'department-operational-records',
  ];
  for (const key of deptKeys) {
    queryClient.invalidateQueries({ queryKey: [key] });
  }
}
