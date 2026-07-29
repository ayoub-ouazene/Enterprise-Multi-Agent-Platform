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
  init: () => void;
}

const TOKEN_STORAGE_KEY = 'orchestra.auth.tokens';

function readStoredTokens(): TokenPair | null {
  try {
    const raw = sessionStorage.getItem(TOKEN_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as TokenPair) : null;
  } catch {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    return null;
  }
}

let _tokens: TokenPair | null =
  typeof sessionStorage === 'undefined' ? null : readStoredTokens();

export function getTokens(): TokenPair | null {
  return _tokens;
}

export function setTokens(tokens: TokenPair | null): void {
  _tokens = tokens;
  if (typeof sessionStorage === 'undefined') return;
  if (tokens) {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
  } else {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

function clearStorage(): void {
  setTokens(null);
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  tokens: _tokens,
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

  init: () => {
    set({ tokens: _tokens, isLoading: Boolean(_tokens) });
  },

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
  useAuthStore.getState().logout();
}
