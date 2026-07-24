import { useQuery } from '@tanstack/react-query';
import { api } from '../client';
import type { LeaveBalanceResponse, LeaveRequestResponse } from '../types';

export function useMyLeaveBalances() {
  return useQuery<LeaveBalanceResponse[]>({
    queryKey: ['employee', 'leave-balances'],
    queryFn: () => api.get<LeaveBalanceResponse[]>('/leave-balances/me'),
    staleTime: 60_000,
  });
}

export function useMyLeaveRequests() {
  return useQuery<LeaveRequestResponse[]>({
    queryKey: ['employee', 'leave-requests'],
    queryFn: () => api.get<LeaveRequestResponse[]>('/leave-requests/me'),
    staleTime: 60_000,
  });
}
