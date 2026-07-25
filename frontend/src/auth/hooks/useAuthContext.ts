import { useAuthStore } from '../store';
import { useShallow } from 'zustand/react/shallow';

export function useAuthContext() {
  return useAuthStore(
    useShallow((state) => ({
      user: state.user,
      isAuthenticated: state.isAuthenticated,
      isLoading: state.isLoading,
      mustChangePassword: state.mustChangePassword,
      onboardingComplete: state.onboardingComplete,
      login: state.setUser,
      logout: state.logout,
      setTokens: state.setTokens,
      setMustChangePassword: state.setMustChangePassword,
      setOnboardingComplete: state.setOnboardingComplete,
      setLoading: state.setLoading,
    })),
  );
}
