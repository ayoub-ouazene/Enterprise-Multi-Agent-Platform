import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../client';
import type { BusinessRequestSummary, BusinessRequestDetail } from '../types';

export interface RequestFilters {
  status?: string;
  priority?: string;
  request_type?: string;
  limit?: number;
  offset?: number;
}

export function useRequests(filters: RequestFilters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.priority) params.set('priority', filters.priority);
  if (filters.request_type) params.set('request_type', filters.request_type);
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters.offset !== undefined) params.set('offset', String(filters.offset));

  const queryString = params.toString();
  const path = `/requests${queryString ? `?${queryString}` : ''}`;

  return useQuery({
    queryKey: ['requests', filters],
    queryFn: () => api.get<BusinessRequestSummary[]>(path),
  });
}

export function useRequest(requestId: string) {
  return useQuery({
    queryKey: ['request', requestId],
    queryFn: () => api.get<BusinessRequestDetail>(`/requests/${requestId}`),
    enabled: !!requestId,
  });
}

export function useCreateRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: { request_type: string; title: string; summary: string; priority?: string }) =>
      api.post<BusinessRequestDetail>('/requests', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requests'] });
    },
  });
}

export function useCancelRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (requestId: string) =>
      api.post<BusinessRequestDetail>(`/requests/${requestId}/cancel`, {}),
    onSuccess: (_data, requestId) => {
      queryClient.invalidateQueries({ queryKey: ['request', requestId] });
      queryClient.invalidateQueries({ queryKey: ['requests'] });
    },
  });
}
