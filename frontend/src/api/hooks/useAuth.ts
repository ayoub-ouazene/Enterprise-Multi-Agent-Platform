import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../client';
import { useAuthStore } from '../../auth/store';
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
      const response = await api.post<TokenPair>(
        '/auth/login',
        credentials,
        { skipAuth: true },
      );
      return response;
    },
    onSuccess: (data) => {
      useAuthStore.getState().setTokens(data);
      queryClient.invalidateQueries({ queryKey: ['me'] });
    },
  });
}

export interface CompanyRegistrationPayload {
  company_name: string;
  company_slug: string;
  email: string;
  password: string;
}

export function useRegisterCompany() {
  return useMutation({
    mutationFn: (payload: CompanyRegistrationPayload) =>
      api.post<TokenPair>('/companies/register', payload, { skipAuth: true }),
    onSuccess: (data) => {
      useAuthStore.getState().setTokens(data);
    },
  });
}

export function useRefreshToken() {
  return useMutation({
    mutationFn: async (refreshToken: string) => {
      const response = await api.post<TokenPair>(
        '/auth/refresh',
        { refresh_token: refreshToken },
        { skipAuth: true },
      );
      return response;
    },
  });
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async (payload: ChangePasswordPayload) => {
      const response = await api.post<{ success: boolean; message: string }>(
        '/auth/change-password',
        payload
      );
      return response;
    },
  });
}

export function useMe(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      const user = await api.get<AuthenticatedUser>('/auth/me');
      const store = useAuthStore.getState();
      store.setUser(user);
      store.setMustChangePassword(user.must_change_password);
      store.setOnboardingComplete(user.onboarding_complete);
      return user;
    },
    retry: false,
    refetchOnWindowFocus: false,
    ...options,
  });
}
