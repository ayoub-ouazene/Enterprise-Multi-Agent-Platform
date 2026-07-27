import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ActorType, type AuthenticatedUser, type DashboardResponse } from '../api/types';
import { DashboardPage } from './DashboardPage';
import { DashboardSection } from './components/DashboardPrimitives';

const state = vi.hoisted(() => ({
  role: 'company' as ActorType,
  error: false,
}));

vi.mock('../auth/hooks/useAuthContext', () => ({
  useAuthContext: () => ({ user: user(state.role) }),
}));
vi.mock('../api/hooks/useDashboard', () => ({
  useDashboard: () => ({
    data: state.error ? undefined : fixture(state.role),
    isLoading: false,
    isError: state.error,
    isFetching: false,
    refetch: vi.fn(),
  }),
}));
vi.mock('../app/providers/SseProvider', () => ({
  useSseConnection: () => ({ connected: true }),
}));

function user(role: ActorType): AuthenticatedUser {
  return {
    user_id: 'u1', company_id: 'c1', email: 'alex@example.com', actor_type: role,
    employee_id: role === ActorType.COMPANY ? null : 'e1',
    department_id: role === ActorType.DEPARTMENT_MANAGER ? 'd1' : null,
    is_manager: role === ActorType.DEPARTMENT_MANAGER, permissions: [],
    company_active: true, onboarding_complete: true, must_change_password: false,
  };
}

function fixture(role: ActorType): DashboardResponse {
  return {
    role,
    identity: {
      company_name: 'Northstar Company', company_active: true, account_label: 'Alex',
      department_name: role === ActorType.DEPARTMENT_MANAGER ? 'Information Technology' : role === ActorType.EMPLOYEE ? 'People Operations' : null,
      department_type: role === ActorType.DEPARTMENT_MANAGER ? 'it' : null,
    },
    metrics: [{ key: 'active', label: 'Active requests', value: 7, detail: 'Authoritative total', status: 'info', href: '/app/requests' }],
    attention: [{ id: 'attention-1', severity: 'warning', title: 'Review access request', explanation: 'A response is required.', resource_type: 'human_action', resource_id: 'a1', action_label: 'Review action', action_url: '/app/human-actions/a1', occurred_at: '2026-07-25T12:00:00Z', due_at: null }],
    active_requests: [{ id: 'r1', title: 'Laptop access', status: 'processing', priority: 'normal', current_stage: 'department_execution', owner_department: role === ActorType.EXTERNAL_USER ? null : 'Information Technology', action_required: false, updated_at: '2026-07-25T12:00:00Z' }],
    completed_requests: [],
    pending_actions: [{ id: 'a1', request_id: 'r1', title: 'Confirm identity', action_type: 'identity_verification', due_at: null, created_at: '2026-07-25T12:00:00Z' }],
    activity: [{ id: 'n1', title: 'Request updated', message: 'A safe progress update is available.', severity: 'info', resource_url: '/app/requests/r1', occurred_at: '2026-07-25T12:00:00Z' }],
    readiness: [{ key: 'policies', label: 'Policies', ready: true, detail: 'Ready' }],
    departments: role === ActorType.COMPANY ? [{ id: 'd1', name: 'Information Technology', department_type: 'it', enabled: true, manager_label: 'manager@example.com', ready: true, active_requests: 2, pending_actions: 0 }] : [],
    generated_at: '2026-07-25T12:00:00Z',
  };
}

describe('role-based dashboard', () => {
  beforeEach(() => { state.error = false; });

  it.each([
    [ActorType.COMPANY, 'Northstar Company overview'],
    [ActorType.DEPARTMENT_MANAGER, 'Information Technology workspace'],
    [ActorType.EMPLOYEE, 'Welcome back, Alex'],
    [ActorType.EXTERNAL_USER, 'How can we help, Alex?'],
  ])('renders the correct dashboard for %s', (role, heading) => {
    state.role = role;
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    expect(screen.getByRole('heading', { level: 1, name: heading })).toBeTruthy();
    if (role === ActorType.EXTERNAL_USER) {
      expect(screen.getByRole('heading', { name: 'Open support requests' })).toBeTruthy();
    } else {
      expect(screen.getByText('7')).toBeTruthy();
    }
  });

  it('keeps manager content department scoped', () => {
    state.role = ActorType.DEPARTMENT_MANAGER;
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    expect(screen.getAllByText(/Information Technology/).length).toBeGreaterThan(0);
    expect(screen.queryByText('Company readiness')).toBeNull();
    expect(screen.queryByText('Human Resources')).toBeNull();
  });

  it('keeps employee and external dashboards free of administration content', () => {
    for (const role of [ActorType.EMPLOYEE, ActorType.EXTERNAL_USER]) {
      state.role = role;
      const view = render(<MemoryRouter><DashboardPage /></MemoryRouter>);
      expect(screen.queryByText('Assign managers')).toBeNull();
      expect(screen.queryByText('Manage policies')).toBeNull();
      expect(document.body.textContent).not.toContain('workflow_state');
      expect(document.body.textContent).not.toContain('decision_package');
      view.unmount();
    }
  });

  it('contains a section-safe complete failure state', () => {
    state.role = ActorType.COMPANY;
    state.error = true;
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    expect(screen.getByRole('heading', { name: 'Dashboard unavailable' })).toBeTruthy();
    expect(screen.getByRole('button', { name: /try again/i })).toBeTruthy();
  });

  it('contains a widget failure without breaking sibling dashboard content', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    function BrokenWidget(): never {
      throw new Error('private backend detail');
    }
    render(<MemoryRouter><p>Healthy sibling</p><DashboardSection title="Workload"><BrokenWidget /></DashboardSection></MemoryRouter>);
    expect(screen.getByText('Healthy sibling')).toBeTruthy();
    expect(screen.getByRole('alert').textContent).toContain('Workload is temporarily unavailable');
    expect(document.body.textContent).not.toContain('private backend detail');
    expect(screen.getByRole('button', { name: /retry section/i })).toBeTruthy();
    consoleError.mockRestore();
  });
});
