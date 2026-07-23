import { useQuery } from '@tanstack/react-query';
import { api } from '../client';
import type { HumanActionSummary } from '../types';

interface HumanActionsParams {
  status?: string;
  overdue_only?: boolean;
  limit?: number;
  offset?: number;
}

export function useHumanActions(params?: HumanActionsParams) {
  const search = new URLSearchParams();
  if (params?.status) search.set('status', params.status);
  if (params?.overdue_only) search.set('overdue_only', String(params.overdue_only));
  if (params?.limit !== undefined) search.set('limit', String(params.limit));
  if (params?.offset !== undefined) search.set('offset', String(params.offset));

  const qs = search.toString();
  const path = `/human-actions${qs ? `?${qs}` : ''}`;

  return useQuery({
    queryKey: ['human-actions', params],
    queryFn: () => api.get<HumanActionSummary[]>(path),
  });
}
