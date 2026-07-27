import { useEffect } from 'react';
import { API_BASE } from '../client';
import { useSseConnection } from '../../app/providers/SseProvider';

export function useRequestSse(requestId: string | undefined) {
  const { connect } = useSseConnection();

  useEffect(() => {
    if (!requestId) return;
    connect(`${API_BASE}/requests/${requestId}/events/stream`);
    return () => {
      connect(`${API_BASE}/notifications/stream`);
    };
  }, [requestId, connect]);
}
