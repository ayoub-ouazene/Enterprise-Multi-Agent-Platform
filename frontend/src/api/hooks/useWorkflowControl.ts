import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../client';
import type { WorkflowControlResponse } from '../types';

export function useWorkflowControl(requestId: string) {
  const queryClient = useQueryClient();

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['request', requestId] });
    queryClient.invalidateQueries({ queryKey: ['workflow-events', requestId] });
    queryClient.invalidateQueries({ queryKey: ['requests'] });
  };

  const start = useMutation({
    mutationFn: () =>
      api.post<WorkflowControlResponse>(`/requests/${requestId}/workflow/start`),
    onSuccess: invalidate,
  });

  const resume = useMutation({
    mutationFn: () =>
      api.post<WorkflowControlResponse>(`/requests/${requestId}/workflow/resume`),
    onSuccess: invalidate,
  });

  const clarify = useMutation({
    mutationFn: (answer: string) =>
      api.post<WorkflowControlResponse>(`/requests/${requestId}/workflow/clarify`, { answer }),
    onSuccess: invalidate,
  });

  return { start, resume, clarify };
}
