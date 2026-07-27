import { useQuery } from '@tanstack/react-query';
import { api } from '../client';
import type { HumanActionSummary } from '../types';

interface HumanActionsParams {
  status?: string;
  request_id?: string;
  overdue_only?: boolean;
  action_type?: string;
  department_id?: string;
  assigned_role?: string;
  due_before?: string;
  due_after?: string;
  limit?: number;
  offset?: number;
}

export function useHumanActions(params?: HumanActionsParams) {
  const search = new URLSearchParams();
  if (params?.status) search.set('status', params.status);
  if (params?.request_id) search.set('request_id', params.request_id);
  if (params?.overdue_only) search.set('overdue_only', String(params.overdue_only));
  if (params?.action_type) search.set('action_type', params.action_type);
  if (params?.department_id) search.set('department_id', params.department_id);
  if (params?.assigned_role) search.set('assigned_role', params.assigned_role);
  if (params?.due_before) search.set('due_before', params.due_before);
  if (params?.due_after) search.set('due_after', params.due_after);
  if (params?.limit !== undefined) search.set('limit', String(params.limit));
  if (params?.offset !== undefined) search.set('offset', String(params.offset));

  const qs = search.toString();
  const path = `/human-actions${qs ? `?${qs}` : ''}`;

  return useQuery({
    queryKey: ['human-actions', params],
    queryFn: () => api.get<HumanActionSummary[]>(path),
    placeholderData: (previous) => previous,
  });
}
