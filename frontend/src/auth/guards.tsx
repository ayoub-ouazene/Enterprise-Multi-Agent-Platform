import { type ReactNode, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthContext } from './hooks/useAuthContext';
import type { AuthenticatedUser } from '../api/types';
import { ActorType } from '../api/types';
import { canAccessAdmin } from './permissions';

interface GuardProps {
  children: ReactNode;
}


export function ProtectedRoute({ children }: GuardProps) {
  const { isAuthenticated, isLoading } = useAuthContext();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/login', { replace: true });
    }
  }, [isLoading, isAuthenticated, navigate]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" role="status">
          <span className="sr-only">Loading...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return null;
  return <>{children}</>;
}

export function UnauthenticatedOnlyRoute({ children }: GuardProps) {
  const { isAuthenticated, isLoading } = useAuthContext();
  const location = useLocation();
  const navigate = useNavigate();

  const from = (location.state as { from?: string })?.from ?? '/app';

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isLoading, isAuthenticated, navigate, from]);

  if (isLoading) return null;
  if (isAuthenticated) return null;
  return <>{children}</>;
}

export function PasswordChangeRoute({ children }: GuardProps) {
  const { mustChangePassword, isLoading } = useAuthContext();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && mustChangePassword) {
      navigate('/change-password', { replace: true });
    }
  }, [isLoading, mustChangePassword, navigate]);

  if (isLoading) return null;
  if (mustChangePassword) return null;
  return <>{children}</>;
}

export function OnboardingRoute({ children }: GuardProps) {
  const { user, onboardingComplete, isLoading } = useAuthContext();
  const navigate = useNavigate();

  const isCompany = user?.actor_type === ActorType.COMPANY;
  const needsOnboarding = isCompany && onboardingComplete === false;

  useEffect(() => {
    if (!isLoading && needsOnboarding) {
      navigate('/app/onboarding', { replace: true });
    }
  }, [isLoading, needsOnboarding, navigate]);

  if (isLoading) return null;
  if (needsOnboarding) return null;
  return <>{children}</>;
}

export function RoleRoute({
  children,
  allowed,
}: GuardProps & { allowed: ActorType[] }) {
  const { user, isLoading } = useAuthContext();
  const navigate = useNavigate();

  const hasRole = user ? allowed.includes(user.actor_type) : false;

  useEffect(() => {
    if (!isLoading && !hasRole) {
      navigate('/access-denied', { replace: true });
    }
  }, [isLoading, hasRole, navigate]);

  if (isLoading) return null;
  if (!hasRole) return null;
  return <>{children}</>;
}

export function AdminRoute({ children }: GuardProps) {
  const { user, isLoading } = useAuthContext();
  const navigate = useNavigate();

  const allowed = canAccessAdmin(user);

  useEffect(() => {
    if (!isLoading && !allowed) {
      navigate('/access-denied', { replace: true });
    }
  }, [isLoading, allowed, navigate]);

  if (isLoading) return null;
  if (!allowed) return null;
  return <>{children}</>;
}

export function PermissionRoute({
  children,
  check,
}: GuardProps & { check: (user: AuthenticatedUser | null) => boolean }) {
  const { user, isLoading } = useAuthContext();
  const navigate = useNavigate();

  const allowed = check(user);

  useEffect(() => {
    if (!isLoading && !allowed) {
      navigate('/access-denied', { replace: true });
    }
  }, [isLoading, allowed, navigate]);

  if (isLoading) return null;
  if (!allowed) return null;
  return <>{children}</>;
}
