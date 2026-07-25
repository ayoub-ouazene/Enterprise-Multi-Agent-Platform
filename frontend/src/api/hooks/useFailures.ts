import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../client';
import type {
  FailureDetailResponse,
  FailureType,
  FailureSource,
  CapabilityGapDetailResponse,
  CapabilityGapSummaryResponse,
  CapabilityGapStatusUpdate,
  CapabilityGapStatus,
} from '../types';

function buildQs(params: Record<string, unknown>): string {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') sp.set(k, String(v));
  });
  const qs = sp.toString();
  return qs ? `?${qs}` : '';
}

/* ===== Failures ===== */

export function useFailures(filters?: {
  failure_type?: FailureType;
  failure_source?: FailureSource;
  resolved?: boolean;
  limit?: number;
  offset?: number;
}) {
  return useQuery<FailureDetailResponse[]>({
    queryKey: ['failures', filters],
    queryFn: () =>
      api.get<FailureDetailResponse[]>(
        `/failures${buildQs(filters ?? {})}`,
      ),
    staleTime: 30_000,
  });
}

/* ===== Capability Gaps ===== */

export function useCapabilityGaps(filters?: {
  status?: CapabilityGapStatus;
  limit?: number;
  offset?: number;
}) {
  return useQuery<CapabilityGapSummaryResponse[]>({
    queryKey: ['capability-gaps', filters],
    queryFn: () =>
      api.get<CapabilityGapSummaryResponse[]>(
        `/capability-gaps${buildQs(filters ?? {})}`,
      ),
    staleTime: 30_000,
  });
}

export function useUpdateCapabilityGapStatus() {
  const queryClient = useQueryClient();
  return useMutation<
    CapabilityGapDetailResponse,
    Error,
    { gapId: string; payload: CapabilityGapStatusUpdate }
  >({
    mutationFn: ({ gapId, payload }) =>
      api.post<CapabilityGapDetailResponse>(
        `/capability-gaps/${gapId}/status`,
        payload,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['capability-gaps'] });
    },
  });
}
