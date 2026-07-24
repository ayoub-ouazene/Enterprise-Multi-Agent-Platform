import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../../auth/store';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export function useRequestSse(requestId: string | undefined) {
  const queryClient = useQueryClient();
  const tokens = useAuthStore((s) => s.tokens);

  useEffect(() => {
    if (!requestId || !tokens?.access_token) return;

    const url = `${API_BASE}/requests/${requestId}/events/stream?token=${encodeURIComponent(tokens.access_token)}`;
    const es = new EventSource(url);

    es.addEventListener('workflow_event', (event) => {
      if (event.data) {
        try {
          const data = JSON.parse(event.data);
          queryClient.invalidateQueries({ queryKey: ['workflow-events', requestId] });
          queryClient.invalidateQueries({ queryKey: ['request', requestId] });
          if (data.event_type === 'waiting_for_human_action' || data.event_type === 'waiting_for_human_approval') {
            queryClient.invalidateQueries({ queryKey: ['human-actions'] });
          }
        } catch {
          // ignore parse errors
        }
      }
    });

    es.addEventListener('error', () => {
      es.close();
    });

    return () => {
      es.close();
    };
  }, [requestId, tokens?.access_token, queryClient]);
}
