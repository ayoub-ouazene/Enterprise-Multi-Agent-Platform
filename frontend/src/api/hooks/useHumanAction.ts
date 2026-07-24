import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../client';
import type { HumanActionSummary, HumanActionSubmitResponse } from '../types';

export function useHumanAction(actionId: string | undefined) {
  return useQuery({
    queryKey: ['human-action', actionId],
    queryFn: () => api.get<HumanActionSummary>(`/human-actions/${actionId}`),
    enabled: !!actionId,
  });
}

export function useSubmitHumanAction(actionId: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: { decision: string; response: string }) =>
      api.post<HumanActionSubmitResponse>(`/human-actions/${actionId}/submit`, payload),
    onSuccess: () => {
      if (actionId) {
        queryClient.invalidateQueries({ queryKey: ['human-action', actionId] });
        queryClient.invalidateQueries({ queryKey: ['human-actions'] });
      }
    },
  });
}
