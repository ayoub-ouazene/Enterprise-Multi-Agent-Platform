import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../client';
import type { HumanActionDetail, HumanActionSubmitResponse } from '../types';

export function useHumanAction(actionId: string | undefined) {
  return useQuery<HumanActionDetail>({
    queryKey: ['human-action', actionId],
    queryFn: () => api.get<HumanActionDetail>(`/human-actions/${actionId}`),
    enabled: !!actionId,
  });
}

export function useSubmitHumanAction(actionId: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: { decision: string; response: string; expected_updated_at?: string }) =>
      api.post<HumanActionSubmitResponse>(`/human-actions/${actionId}/submit`, payload),
    onSuccess: () => {
      if (actionId) {
        const action = queryClient.getQueryData<HumanActionDetail>(['human-action', actionId]);
        queryClient.invalidateQueries({ queryKey: ['human-action', actionId] });
        queryClient.invalidateQueries({ queryKey: ['human-actions'] });
        queryClient.invalidateQueries({ queryKey: ['notifications'] });
        queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] });
        queryClient.invalidateQueries({ queryKey: ['dashboard'] });
        if (action?.request_id) {
          queryClient.invalidateQueries({ queryKey: ['request', action.request_id] });
          queryClient.invalidateQueries({ queryKey: ['workflow-events', action.request_id] });
        }
      }
    },
  });
}

/** Structured submit: serializes `fields` to JSON in the `response` payload field. */
export function useSubmitStructuredHumanAction(actionId: string | undefined) {
  const base = useSubmitHumanAction(actionId);
  const queryClient = useQueryClient();

  return {
    ...base,
    submit(decision: string, fields: Record<string, unknown>, options?: Parameters<typeof base.mutate>[1]) {
      const action = queryClient.getQueryData<HumanActionDetail>(['human-action', actionId]);
      base.mutate({ decision, response: JSON.stringify(fields), expected_updated_at: action?.updated_at }, options);
    },
  };
}
