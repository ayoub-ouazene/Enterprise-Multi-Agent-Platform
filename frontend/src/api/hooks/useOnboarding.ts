import { useQuery } from '@tanstack/react-query';
import { api } from '../client';
import type { OnboardingStatus, ImportJob } from '../types';

export function useOnboardingStatus() {
  return useQuery({
    queryKey: ['onboarding', 'status'],
    queryFn: () => api.get<OnboardingStatus>('/onboarding/status'),
  });
}

export function useImportJobs(filters?: { import_type?: string; status?: string; limit?: number; offset?: number }) {
  const params = new URLSearchParams();
  if (filters?.import_type) params.set('import_type', filters.import_type);
  if (filters?.status) params.set('status', filters.status);
  if (filters?.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters?.offset !== undefined) params.set('offset', String(filters.offset));

  const queryString = params.toString();
  const path = `/onboarding/imports${queryString ? `?${queryString}` : ''}`;

  return useQuery({
    queryKey: ['onboarding', 'imports', filters],
    queryFn: () => api.get<ImportJob[]>(path),
  });
}
