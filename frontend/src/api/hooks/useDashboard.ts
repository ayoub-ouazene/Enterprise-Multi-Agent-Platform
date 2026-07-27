import { useQuery } from '@tanstack/react-query';
import { api } from '../client';
import type { DashboardResponse } from '../types';

export const dashboardQueryKey = ['dashboard'] as const;

export function useDashboard() {
  return useQuery({
    queryKey: dashboardQueryKey,
    queryFn: () => api.get<DashboardResponse>('/dashboard'),
    staleTime: 15_000,
    placeholderData: (previous) => previous,
  });
}
