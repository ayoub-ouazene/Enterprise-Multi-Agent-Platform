import { useQuery } from '@tanstack/react-query';
import { api } from '../client';
import type {
  DepartmentStatsResponse,
  DepartmentReadinessResponse,
  DepartmentActivityResponse,
  BusinessRequestSummary,
  HumanActionSummary,
  DepartmentOperationalRecord,
} from '../types';

export function useDepartments() {
  return useQuery({
    queryKey: ['departments'],
    queryFn: () => api.get<{ id: string; name: string; department_type: string; is_active: boolean }[]>('/departments'),
  });
}

export function useDepartmentStats(deptType: string) {
  return useQuery({
    queryKey: ['department-stats', deptType],
    queryFn: () => api.get<DepartmentStatsResponse>(`/departments/${deptType}/stats`),
    enabled: !!deptType,
  });
}

export function useDepartmentRequests(
  deptType: string,
  filters: { status?: string; limit?: number; offset?: number } = {}
) {
  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters.offset !== undefined) params.set('offset', String(filters.offset));
  const qs = params.toString();
  return useQuery({
    queryKey: ['department-requests', deptType, filters],
    queryFn: () =>
      api.get<BusinessRequestSummary[]>(`/departments/${deptType}/requests${qs ? `?${qs}` : ''}`),
    enabled: !!deptType,
  });
}

export function useDepartmentActions(
  deptType: string,
  filters: { status?: string; limit?: number; offset?: number } = {}
) {
  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters.offset !== undefined) params.set('offset', String(filters.offset));
  const qs = params.toString();
  return useQuery({
    queryKey: ['department-actions', deptType, filters],
    queryFn: () =>
      api.get<HumanActionSummary[]>(`/departments/${deptType}/actions${qs ? `?${qs}` : ''}`),
    enabled: !!deptType,
  });
}

export function useDepartmentReadiness(deptType: string) {
  return useQuery({
    queryKey: ['department-readiness', deptType],
    queryFn: () => api.get<DepartmentReadinessResponse>(`/departments/${deptType}/readiness`),
    enabled: !!deptType,
  });
}

export function useDepartmentActivity(deptType: string, limit = 20) {
  return useQuery({
    queryKey: ['department-activity', deptType, limit],
    queryFn: () =>
      api.get<DepartmentActivityResponse[]>(`/departments/${deptType}/activity?limit=${limit}`),
    enabled: !!deptType,
  });
}

export function useDepartmentOperationalRecords(
  deptType: string,
  filters: { kind?: string; limit?: number } = {},
) {
  const params = new URLSearchParams();
  if (filters.kind) params.set('kind', filters.kind);
  params.set('limit', String(filters.limit ?? 30));
  return useQuery({
    queryKey: ['department-operational-records', deptType, filters],
    queryFn: () =>
      api.get<DepartmentOperationalRecord[]>(
        `/departments/${deptType}/operational-records?${params.toString()}`,
      ),
    enabled: Boolean(deptType),
  });
}
