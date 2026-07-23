import { create } from 'zustand';
import type { AuthenticatedUser } from '../api/types';

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  access_token_expires_in: number;
  refresh_token_expires_in: number;
}

interface AuthState {
  user: AuthenticatedUser | null;
  tokens: TokenPair | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  mustChangePassword: boolean;
  onboardingComplete: boolean | null;
  setUser: (user: AuthenticatedUser | null) => void;
  setTokens: (tokens: TokenPair | null) => void;
  setMustChangePassword: (value: boolean) => void;
  setOnboardingComplete: (value: boolean) => void;
  setLoading: (value: boolean) => void;
  logout: () => void;
}

let _tokens: TokenPair | null = null;

export function getTokens(): TokenPair | null {
  return _tokens;
}

export function setTokens(tokens: TokenPair | null): void {
  _tokens = tokens;
}

function clearStorage(): void {
  _tokens = null;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  tokens: null,
  isAuthenticated: false,
  isLoading: true,
  mustChangePassword: false,
  onboardingComplete: null,

  setUser: (user) => set({ user, isAuthenticated: !!user }),
  setTokens: (tokens) => {
    setTokens(tokens);
    set({ tokens });
  },
  setMustChangePassword: (value) => set({ mustChangePassword: value }),
  setOnboardingComplete: (value) => set({ onboardingComplete: value }),
  setLoading: (value) => set({ isLoading: value }),

  logout: () => {
    clearStorage();
    set({
      user: null,
      tokens: null,
      isAuthenticated: false,
      isLoading: false,
      mustChangePassword: false,
      onboardingComplete: null,
    });
  },
}));

export function clearAuth(): void {
  clearStorage();
}
