import { useQuery } from '@tanstack/react-query';
import { api } from '../client';
import type { WorkflowEvent } from '../types';

export function useWorkflowEvents(requestId: string) {
  return useQuery({
    queryKey: ['workflow-events', requestId],
    queryFn: () => api.get<WorkflowEvent[]>(`/requests/${requestId}/events`),
    enabled: !!requestId,
    refetchInterval: 5000,
  });
}
