import { beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryProvider } from '../providers/QueryProvider';
import { LoginPage } from './LoginPage';
import { SignupPage } from './SignupPage';
import { ChangePasswordPage } from './ChangePasswordPage';
import { ActorType } from '../../api/types';
import { ApiErrorException } from '../../api/client';

const { login, registerCompany, changePassword, getMe } = vi.hoisted(() => ({
  login: vi.fn(),
  registerCompany: vi.fn(),
  changePassword: vi.fn(),
  getMe: vi.fn(),
}));

vi.mock('../../api/hooks/useAuth', () => ({
  useLogin: () => ({ mutateAsync: login, isPending: false }),
  useRegisterCompany: () => ({ mutateAsync: registerCompany, isPending: false }),
  useChangePassword: () => ({ mutateAsync: changePassword, isPending: false }),
}));

vi.mock('../../api/client', async (importOriginal) => {
  const original = await importOriginal<typeof import('../../api/client')>();
  return {
    ...original,
    api: { ...original.api, get: getMe },
  };
});

function renderAt(element: React.ReactNode, path: string) {
  return render(
    <QueryProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path={path} element={element} />
          <Route path="/app/onboarding" element={<div>Onboarding destination</div>} />
          <Route path="/app" element={<div>Application destination</div>} />
        </Routes>
      </MemoryRouter>
    </QueryProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  login.mockResolvedValue({
    access_token: 'access',
    refresh_token: 'refresh',
    access_token_expires_in: 1800,
    refresh_token_expires_in: 604800,
  });
  registerCompany.mockResolvedValue({
    access_token: 'access',
    refresh_token: 'refresh',
    access_token_expires_in: 1800,
    refresh_token_expires_in: 604800,
  });
  changePassword.mockResolvedValue({ success: true });
  getMe.mockResolvedValue({
    user_id: 'user',
    company_id: 'company',
    email: 'owner@example.com',
    actor_type: ActorType.COMPANY,
    employee_id: null,
    department_id: null,
    is_manager: false,
    permissions: [],
    company_active: false,
    onboarding_complete: false,
    must_change_password: false,
  });
});

describe('public authentication forms', () => {
  it('submits only backend-supported Company registration fields', async () => {
    renderAt(<SignupPage />, '/signup');
    fireEvent.change(screen.getByLabelText('Company name'), { target: { value: 'Northwind' } });
    fireEvent.change(screen.getByLabelText('Workspace address'), { target: { value: 'northwind' } });
    fireEvent.change(screen.getByLabelText('Company account email'), { target: { value: 'owner@example.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'StrongPassword12' } });
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'StrongPassword12' } });
    fireEvent.click(screen.getByRole('button', { name: /create company workspace/i }));

    await waitFor(() => expect(registerCompany).toHaveBeenCalledTimes(1));
    expect(registerCompany).toHaveBeenCalledWith({
      company_name: 'Northwind',
      company_slug: 'northwind',
      email: 'owner@example.com',
      password: 'StrongPassword12',
    });
    expect(await screen.findByText('Onboarding destination')).toBeTruthy();
  });

  it('submits the real workspace login contract', async () => {
    getMe.mockResolvedValueOnce({
      user_id: 'external',
      company_id: 'company',
      email: 'requester@example.com',
      actor_type: ActorType.EXTERNAL_USER,
      employee_id: null,
      department_id: null,
      is_manager: false,
      permissions: [],
      company_active: true,
      onboarding_complete: true,
      must_change_password: false,
    });
    renderAt(<LoginPage />, '/login');
    fireEvent.change(screen.getByLabelText('Company workspace'), { target: { value: 'northwind' } });
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'requester@example.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'SecretPassword12' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in securely/i }));

    await waitFor(() => expect(login).toHaveBeenCalledWith({
      company_slug: 'northwind',
      email: 'requester@example.com',
      password: 'SecretPassword12',
    }));
    expect(await screen.findByText('Application destination')).toBeTruthy();
  });

  it('distinguishes connection failures from invalid credentials', async () => {
    login.mockRejectedValueOnce(new ApiErrorException({
      status: 0,
      code: 'NETWORK_ERROR',
      message: 'Unable to connect',
      retryable: true,
    }));
    renderAt(<LoginPage />, '/login');
    fireEvent.change(screen.getByLabelText('Company workspace'), { target: { value: 'northwind' } });
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'owner@example.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'IncorrectPassword' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in securely/i }));
    expect(await screen.findByText(/service cannot be reached/i)).toBeTruthy();

    cleanup();
    login.mockRejectedValueOnce(new ApiErrorException({
      status: 401,
      code: 'UNAUTHORIZED',
      message: 'Invalid authentication credentials',
      retryable: false,
    }));
    renderAt(<LoginPage />, '/login');
    fireEvent.change(screen.getByLabelText('Company workspace'), { target: { value: 'northwind' } });
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'owner@example.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'IncorrectPassword' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in securely/i }));
    expect(await screen.findByText(/workspace, email, or password is incorrect/i)).toBeTruthy();
  });

  it('prevents a duplicate signup submission while the first is pending', async () => {
    registerCompany.mockReturnValue(new Promise(() => undefined));
    renderAt(<SignupPage />, '/signup');
    fireEvent.change(screen.getByLabelText('Company name'), { target: { value: 'Contoso' } });
    fireEvent.change(screen.getByLabelText('Workspace address'), { target: { value: 'contoso' } });
    fireEvent.change(screen.getByLabelText('Company account email'), { target: { value: 'owner@contoso.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'StrongPassword12' } });
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'StrongPassword12' } });
    const submit = screen.getByRole('button', { name: /create company workspace/i });
    fireEvent.click(submit);
    fireEvent.click(submit);
    await waitFor(() => expect(registerCompany).toHaveBeenCalledTimes(1));
  });

  it('completes the forced-password-change contract', async () => {
    renderAt(<ChangePasswordPage />, '/change-password');
    fireEvent.change(screen.getByLabelText('Current temporary password'), { target: { value: 'TemporaryPassword12' } });
    fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'NewPrivatePassword12' } });
    fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'NewPrivatePassword12' } });
    fireEvent.click(screen.getByRole('button', { name: /update password and continue/i }));
    await waitFor(() => expect(changePassword).toHaveBeenCalledWith({
      current_password: 'TemporaryPassword12',
      new_password: 'NewPrivatePassword12',
    }));
    expect(await screen.findByText(/your workspace is ready/i)).toBeTruthy();
  });
});
