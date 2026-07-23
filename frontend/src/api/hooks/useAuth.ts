import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../client';
import { useAuthStore, setTokens } from '../../auth/store';
import type { AuthenticatedUser } from '../../api/types';
import type { TokenPair } from '../../auth/store';

export interface LoginCredentials {
  company_slug: string;
  email: string;
  password: string;
}

export interface RefreshPayload {
  refresh_token: string;
}

export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      const response = await api.post<TokenPair>('/auth/login', credentials);
      return response;
    },
    onSuccess: (data) => {
      setTokens(data);
      useAuthStore.getState().setTokens(data);
      queryClient.invalidateQueries({ queryKey: ['me'] });
    },
  });
}

export function useRefreshToken() {
  return useMutation({
    mutationFn: async (refreshToken: string) => {
      const response = await api.post<TokenPair>('/auth/refresh', {
        refresh_token: refreshToken,
      });
      return response;
    },
  });
}

export function useMe(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      const user = await api.get<AuthenticatedUser>('/auth/me');
      useAuthStore.getState().setUser(user);
      return user;
    },
    retry: false,
    refetchOnWindowFocus: false,
    ...options,
  });
}
