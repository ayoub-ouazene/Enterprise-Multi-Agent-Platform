import { beforeEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ActorType, type AuthenticatedUser } from '../api/types';
import { OnboardingRoute, ProtectedRoute } from './guards';
import { useAuthStore } from './store';


function company(active: boolean): AuthenticatedUser {
  return {
    user_id: '00000000-0000-0000-0000-000000000001',
    company_id: '00000000-0000-0000-0000-000000000002',
    email: 'owner@example.com',
    actor_type: ActorType.COMPANY,
    employee_id: null,
    department_id: null,
    is_manager: false,
    permissions: [],
    company_active: active,
    onboarding_complete: active,
    must_change_password: false,
  };
}

describe('authentication route guards', () => {
  beforeEach(() => {
    sessionStorage.clear();
    useAuthStore.getState().logout();
    useAuthStore.getState().setLoading(false);
  });

  it('sends unauthenticated users to login with their return path', async () => {
    render(
      <MemoryRouter initialEntries={['/app/requests']}>
        <Routes>
          <Route path="/login" element={<div>Login page</div>} />
          <Route path="/app/requests" element={<ProtectedRoute><div>Requests</div></ProtectedRoute>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByText('Login page')).toBeTruthy();
  });

  it('redirects an inactive Company to onboarding', async () => {
    useAuthStore.getState().setUser(company(false));
    render(
      <MemoryRouter initialEntries={['/app/overview']}>
        <Routes>
          <Route path="/app/onboarding" element={<div>Onboarding page</div>} />
          <Route path="/app/overview" element={<OnboardingRoute><div>Dashboard</div></OnboardingRoute>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByText('Onboarding page')).toBeTruthy();
  });

  it('does not guard the onboarding route with itself', () => {
    useAuthStore.getState().setUser(company(false));
    render(
      <MemoryRouter initialEntries={['/app/onboarding']}>
        <Routes>
          <Route path="/app/onboarding" element={<ProtectedRoute><div>Onboarding page</div></ProtectedRoute>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText('Onboarding page')).toBeTruthy();
  });
});
