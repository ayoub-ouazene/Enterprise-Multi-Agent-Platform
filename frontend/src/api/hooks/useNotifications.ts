import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../client';
import type { Notification } from '../types';

interface UnreadCountResponse {
  unread_count: number;
}

interface ReadAllResponse {
  updated_count: number;
}

export function useNotifications(filters?: { is_read?: boolean; limit?: number; offset?: number }) {
  const params = new URLSearchParams();
  if (filters?.is_read !== undefined) params.set('is_read', String(filters.is_read));
  if (filters?.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters?.offset !== undefined) params.set('offset', String(filters.offset));

  const queryString = params.toString();
  const path = `/notifications${queryString ? `?${queryString}` : ''}`;

  return useQuery({
    queryKey: ['notifications', filters],
    queryFn: () => api.get<Notification[]>(path),
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: ['notifications', 'unread'],
    queryFn: () => api.get<UnreadCountResponse>('/notifications/unread-count'),
    refetchInterval: 60_000,
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notificationId: string) =>
      api.post<Notification>(`/notifications/${notificationId}/read`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.post<ReadAllResponse>('/notifications/read-all', {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] });
    },
  });
}
