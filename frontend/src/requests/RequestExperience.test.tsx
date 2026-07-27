import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ActorType, RequestPriority, RequestStatus, type AuthenticatedUser, type BusinessRequestDetail } from '../api/types';
import { ApiErrorException } from '../api/errors';
import { RequestsPage } from '../app/pages/RequestsPage';
import { NewRequestPage } from '../app/pages/NewRequestPage';
import { RequestDetailPage } from '../app/pages/RequestDetailPage';

const state = vi.hoisted(() => ({
  role: 'employee' as ActorType,
  create: vi.fn(),
  cancel: vi.fn(),
  clarify: vi.fn(),
  start: vi.fn(),
  requests: [] as BusinessRequestDetail[],
  detail: null as BusinessRequestDetail | null,
  events: [] as Record<string, unknown>[],
}));

vi.mock('../auth/hooks/useAuthContext', () => ({
  useAuthContext: () => ({ user: authUser(state.role) }),
}));
vi.mock('../api/hooks/useRequests', () => ({
  useRequests: () => ({ data: state.requests, isLoading: false, isFetching: false, isError: false, refetch: vi.fn() }),
  useCreateRequest: () => ({ mutateAsync: state.create, isPending: false }),
  useRequest: () => ({ data: state.detail, isLoading: false, isError: false, refetch: vi.fn() }),
  useCancelRequest: () => ({ mutateAsync: state.cancel, isPending: false }),
}));
vi.mock('../api/hooks/useWorkflowControl', () => ({
  useWorkflowControl: () => ({
    start: { mutate: state.start, isPending: false },
    clarify: { mutateAsync: state.clarify, isPending: false },
    resume: { mutate: vi.fn(), isPending: false },
  }),
}));
vi.mock('../api/hooks/useWorkflowEvents', () => ({
  useWorkflowEvents: () => ({ data: state.events, isLoading: false, refetch: vi.fn() }),
}));
vi.mock('../api/hooks/useRequestSse', () => ({ useRequestSse: vi.fn() }));
vi.mock('../app/providers/SseProvider', () => ({
  useSseConnection: () => ({ connected: true, connect: vi.fn(), disconnect: vi.fn() }),
}));

function authUser(role: ActorType): AuthenticatedUser {
  return {
    user_id: 'user-1', company_id: 'company-1', email: `${role}@example.com`,
    actor_type: role, employee_id: role === ActorType.COMPANY ? null : 'employee-1',
    department_id: role === ActorType.DEPARTMENT_MANAGER ? 'department-1' : null,
    is_manager: role === ActorType.DEPARTMENT_MANAGER, permissions: [],
    company_active: true, onboarding_complete: true, must_change_password: false,
  };
}

function detail(overrides: Partial<BusinessRequestDetail> = {}): BusinessRequestDetail {
  return {
    id: 'request-1234-5678',
    request_type: 'software_access',
    title: 'Access reporting workspace',
    summary: 'Provide access to the reporting workspace.',
    status: RequestStatus.PROCESSING,
    current_stage: 'department_execution',
    priority: RequestPriority.NORMAL,
    owner_department_id: 'department-1',
    active_department_id: 'department-1',
    owner_department: { id: 'department-1', name: 'Information Technology', department_type: 'it' },
    active_department: { id: 'department-1', name: 'Information Technology', department_type: 'it' },
    requester_user_id: 'user-1',
    requester_label: 'employee@example.com',
    attention_required: false,
    pending_action_count: 0,
    can_cancel: true,
    created_at: '2026-07-25T10:00:00Z',
    updated_at: '2026-07-25T11:00:00Z',
    requester_employee_id: 'employee-1',
    final_decision: null,
    final_reason: null,
    completed_at: null,
    cancelled_at: null,
    failed_at: null,
    current_state_summary: 'The owner department is working on the request.',
    clarification: null,
    collaboration_summary: null,
    quality_check_summary: null,
    failure_summary: null,
    final_result: null,
    connected_actions: [],
    allowed_actions: ['cancel'],
    ...overrides,
  };
}

describe('Business Request experience', () => {
  beforeEach(() => {
    state.role = ActorType.EMPLOYEE;
    state.create.mockReset();
    state.cancel.mockReset();
    state.clarify.mockReset();
    state.start.mockReset();
    state.requests = [];
    state.detail = detail();
    state.events = [];
    sessionStorage.clear();
  });

  it('keeps requester identity out of an external-user request list', () => {
    state.role = ActorType.EXTERNAL_USER;
    state.requests = [detail({ requester_label: 'private-employee@example.com', owner_department: null, active_department: null })];
    render(<MemoryRouter><RequestsPage /></MemoryRouter>);
    expect(screen.getAllByText('Access reporting workspace')).toHaveLength(2);
    expect(document.body.textContent).not.toContain('private-employee@example.com');
    expect(screen.queryByText('Requester')).toBeNull();
  });

  it('shows authoritative Router processing and starts a newly created request once', async () => {
    state.detail = detail({
      status: RequestStatus.CREATED,
      owner_department_id: null,
      active_department_id: null,
      owner_department: null,
      active_department: null,
      current_state_summary: 'The request was received and is ready for routing.',
    });
    render(<MemoryRouter initialEntries={[`/app/requests/${state.detail.id}`]}><Routes><Route path="/app/requests/:requestId" element={<RequestDetailPage />} /></Routes></MemoryRouter>);
    expect(screen.getAllByText('Submitted').length).toBeGreaterThan(0);
    expect(screen.getByText('The request was received and is ready for routing.')).toBeTruthy();
    await waitFor(() => expect(state.start).toHaveBeenCalledTimes(1));
  });

  it('submits only approved employee fields, prevents duplicate clicks, and navigates after an ID exists', async () => {
    let resolveCreate: (value: BusinessRequestDetail) => void = () => undefined;
    state.create.mockReturnValue(new Promise((resolve) => { resolveCreate = resolve; }));
    render(<MemoryRouter initialEntries={['/app/requests/new']}><Routes><Route path="/app/requests/new" element={<NewRequestPage />} /><Route path="/app/requests/:requestId" element={<p>Request detail reached</p>} /></Routes></MemoryRouter>);
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Request analytics access' } });
    fireEvent.change(screen.getByLabelText('Request type'), { target: { value: 'software_access' } });
    fireEvent.change(screen.getByLabelText('Detailed description'), { target: { value: 'Access is required for monthly reporting work.' } });
    const submit = screen.getByRole('button', { name: 'Submit request' });
    fireEvent.click(submit);
    fireEvent.click(submit);
    await waitFor(() => expect(state.create).toHaveBeenCalledTimes(1));
    expect(state.create).toHaveBeenCalledWith({
      request_type: 'software_access',
      title: 'Request analytics access',
      summary: 'Access is required for monthly reporting work.',
    });
    expect(screen.queryByText('Request detail reached')).toBeNull();
    resolveCreate(detail());
    expect(await screen.findByText('Request detail reached')).toBeTruthy();
    expect(sessionStorage.getItem('tellus.request.draft')).toBeNull();
  });

  it('renders clarification, collaboration, quality check, safe actions, and plain-text results without internals', () => {
    state.detail = detail({
      status: RequestStatus.UNDER_REVIEW,
      clarification: { question: 'Which reporting workspace?', number: 2, maximum: 3 },
      collaboration_summary: 'A collaborating department is currently assisting the owner department.',
      quality_check_summary: 'A quality check is in progress before the workflow continues.',
      connected_actions: [{ id: 'action-1', title: 'Confirm access scope', action_type: 'information_request', status: 'pending', due_at: null, assigned_role: null, can_respond: true, action_url: '/app/human-actions/action-1' }],
      final_result: { title: 'Safe result', summary: '<img src=x onerror=alert(1)> Approved safely', limitations: [], next_steps: [], sources: [{ document_id: 'doc-1', title: 'Access policy', version: '3', section: 'Eligibility', scope: 'it' }] },
    });
    state.events = [{ id: 'event-1', request_id: state.detail.id, event_type: 'department_collaboration_started', title: 'Technical assistance started', message: 'An authorized department is assisting.', actor_label: 'Department', department_id: 'department-1', sequence_number: 1, created_at: '2026-07-25T10:30:00Z' }];
    render(<MemoryRouter initialEntries={[`/app/requests/${state.detail.id}`]}><Routes><Route path="/app/requests/:requestId" element={<RequestDetailPage />} /></Routes></MemoryRouter>);
    expect(screen.getByText('Which reporting workspace?')).toBeTruthy();
    expect(screen.getByText(/collaborating department/i)).toBeTruthy();
    expect(screen.getAllByText(/quality check/i).length).toBeGreaterThan(0);
    expect(screen.getByText('Confirm access scope')).toBeTruthy();
    expect(screen.getByText('<img src=x onerror=alert(1)> Approved safely')).toBeTruthy();
    expect(document.querySelector('img[src="x"]')).toBeNull();
    expect(document.body.textContent).not.toContain('workflow_state');
    expect(document.body.textContent).not.toContain('decision_package');
  });

  it('distinguishes the owner from the temporarily assisting department', () => {
    state.detail = detail({
      status: RequestStatus.WAITING_FOR_DEPARTMENT,
      current_state_summary: 'Another authorized department is assisting.',
      owner_department: { id: 'department-1', name: 'Customer Support', department_type: 'customer_support' },
      active_department: { id: 'department-2', name: 'Information Technology', department_type: 'it' },
      active_department_id: 'department-2',
      collaboration_summary: 'Customer Support requested technical assistance.',
    });
    render(<MemoryRouter initialEntries={[`/app/requests/${state.detail.id}`]}><Routes><Route path="/app/requests/:requestId" element={<RequestDetailPage />} /></Routes></MemoryRouter>);
    expect(screen.getByText('Owner: Customer Support')).toBeTruthy();
    expect(screen.getByText('Assisting: Information Technology')).toBeTruthy();
    expect(screen.getByText('Customer Support requested technical assistance.')).toBeTruthy();
  });

  it('submits one clarification answer and waits for server confirmation', async () => {
    state.detail = detail({ clarification: { question: 'Which application?', number: 1, maximum: 3 }, allowed_actions: ['answer_clarification'] });
    state.clarify.mockResolvedValue({ request_id: state.detail.id });
    render(<MemoryRouter initialEntries={[`/app/requests/${state.detail.id}`]}><Routes><Route path="/app/requests/:requestId" element={<RequestDetailPage />} /></Routes></MemoryRouter>);
    fireEvent.change(screen.getByLabelText('Your answer'), { target: { value: 'The reporting portal' } });
    const submit = screen.getByRole('button', { name: 'Submit answer' });
    fireEvent.click(submit);
    fireEvent.click(submit);
    await waitFor(() => expect(state.clarify).toHaveBeenCalledTimes(1));
    expect(state.clarify).toHaveBeenCalledWith('The reporting portal');
    expect(await screen.findByText(/answer was confirmed/i)).toBeTruthy();
    expect(sessionStorage.getItem(`tellus.clarification.${state.detail.id}`)).toBeNull();
  });

  it('handles a stale clarification response without losing the session answer', async () => {
    state.detail = detail({ clarification: { question: 'Which application?', number: 1, maximum: 3 }, allowed_actions: ['answer_clarification'] });
    state.clarify.mockRejectedValue(new ApiErrorException({ status: 409, code: 'CONFLICT', message: 'Conflict', retryable: true }));
    render(<MemoryRouter initialEntries={[`/app/requests/${state.detail.id}`]}><Routes><Route path="/app/requests/:requestId" element={<RequestDetailPage />} /></Routes></MemoryRouter>);
    fireEvent.change(screen.getByLabelText('Your answer'), { target: { value: 'The finance reporting portal' } });
    fireEvent.click(screen.getByRole('button', { name: 'Submit answer' }));
    expect(await screen.findByText(/already answered or the request changed/i)).toBeTruthy();
    expect(sessionStorage.getItem(`tellus.clarification.${state.detail.id}`)).toBe('The finance reporting portal');
  });

  it('confirms cancellation and reports an authoritative conflict', async () => {
    state.cancel.mockRejectedValue(new ApiErrorException({ status: 409, code: 'CONFLICT', message: 'Conflict', retryable: true }));
    render(<MemoryRouter initialEntries={[`/app/requests/${state.detail!.id}`]}><Routes><Route path="/app/requests/:requestId" element={<RequestDetailPage />} /></Routes></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: 'Cancel request' }));
    expect(screen.getByRole('dialog', { name: 'Cancel this request?' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Confirm cancellation' }));
    expect(await screen.findByText(/changed and can no longer be cancelled/i)).toBeTruthy();
    expect(state.cancel).toHaveBeenCalledWith(state.detail!.id);
  });
});
