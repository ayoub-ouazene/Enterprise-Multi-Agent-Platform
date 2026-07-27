import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { HumanActionDetail } from '../api/types';
import { HumanActionsPage } from '../app/pages/HumanActionsPage';
import { HumanActionDetailPage } from '../app/pages/HumanActionDetailPage';

const state = vi.hoisted(() => ({
  actions: [] as HumanActionDetail[],
  action: null as HumanActionDetail | null,
  submit: vi.fn(),
}));
vi.mock('../api/hooks/useHumanActions', () => ({ useHumanActions: () => ({ data: state.actions, isLoading: false, isError: false }) }));
vi.mock('../api/hooks/useDepartments', () => ({ useDepartments: () => ({ data: [] }) }));
vi.mock('../api/hooks/useHumanAction', () => ({
  useHumanAction: () => ({ data: state.action, isLoading: false, error: null, refetch: vi.fn() }),
  useSubmitStructuredHumanAction: () => ({ submit: state.submit, isPending: false, isSuccess: false }),
}));
vi.mock('../api/hooks/useRequestSse', () => ({ useRequestSse: vi.fn() }));

function action(overrides: Partial<HumanActionDetail> = {}): HumanActionDetail {
  return {
    id: 'action-1', request_id: 'request-1234', action_type: 'finance_purchase_approval',
    title: 'Approve analytics purchase', status: 'pending', assigned_role: 'company',
    due_date: '2026-07-28T10:00:00Z', resolved_at: null,
    created_at: '2026-07-26T10:00:00Z', updated_at: '2026-07-26T10:00:00Z',
    allowed_decisions: ['approved', 'rejected'], can_respond: true,
    request_title: 'Analytics purchase', request_status: 'waiting_for_human_approval',
    requesting_department: 'Finance', description: 'Review the prepared purchase.',
    safe_context: { amount: '1250.50', currency: 'USD', private_budget_record: 'hidden', summary: '<img src=x onerror=alert(1)>' },
    resolution_decision: null, resolution_comment: null,
    related_request: { id: 'request-1234', title: 'Analytics purchase', status: 'waiting_for_human_approval', owner_department: 'Finance' },
    history: [{ event: 'created', title: 'Action created', description: 'Assigned safely.', occurred_at: '2026-07-26T10:00:00Z' }],
    ...overrides,
  };
}

describe('HumanAction experience', () => {
  beforeEach(() => { state.actions = []; state.action = action(); state.submit.mockReset(); });

  it('keeps confidential decision-package fields out of inbox rows', () => {
    state.actions = [action()];
    render(<MemoryRouter><HumanActionsPage /></MemoryRouter>);
    expect(screen.getByText('Approve analytics purchase')).toBeTruthy();
    expect(document.body.textContent).not.toContain('private_budget_record');
    expect(document.body.textContent).not.toContain('1250.50');
  });

  it('renders decimal strings and allowlisted context as text, never HTML', () => {
    render(<MemoryRouter initialEntries={['/app/human-actions/action-1']}><Routes><Route path="/app/human-actions/:actionId" element={<HumanActionDetailPage />} /></Routes></MemoryRouter>);
    expect(screen.getByText('1250.50')).toBeTruthy();
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeTruthy();
    expect(document.querySelector('img[src="x"]')).toBeNull();
    expect(document.body.textContent).not.toContain('private_budget_record');
  });

  it('requires a rejection comment and uses deliberate confirmation', async () => {
    render(<MemoryRouter initialEntries={['/app/human-actions/action-1']}><Routes><Route path="/app/human-actions/:actionId" element={<HumanActionDetailPage />} /></Routes></MemoryRouter>);
    fireEvent.click(screen.getByLabelText('rejected'));
    fireEvent.click(screen.getByRole('button', { name: /reject action/i }));
    expect(screen.getByText(/explain a rejection/i)).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/comment/i), { target: { value: 'Budget threshold requires rejection.' } });
    fireEvent.click(screen.getByRole('button', { name: /reject action/i }));
    expect(screen.getByRole('dialog', { name: /confirm reject action/i })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Confirm reject action' }));
    await waitFor(() => expect(state.submit).toHaveBeenCalledTimes(1));
    expect(state.submit.mock.calls[0][0]).toBe('rejected');
  });

  it('allows exactly one eligible supplier and explains the terminal consequence', () => {
    state.action = action({
      action_type: 'supplier_selection',
      allowed_decisions: ['selected'],
      safe_context: {
        candidates: [
          { id: 'alpha', supplier: 'Alpha Supply', eligible: true, total_cost: '1200.00', currency: 'USD' },
          { id: 'beta', supplier: 'Beta Supply', eligible: false, reason: 'Compliance expired' },
        ],
      },
    });
    render(<MemoryRouter initialEntries={['/app/human-actions/action-1']}><Routes><Route path="/app/human-actions/:actionId" element={<HumanActionDetailPage />} /></Routes></MemoryRouter>);
    fireEvent.click(screen.getByLabelText('selected'));
    expect((screen.getByLabelText(/Beta Supply/i) as HTMLInputElement).disabled).toBe(true);
    fireEvent.click(screen.getByLabelText(/Alpha Supply/i));
    fireEvent.click(screen.getByRole('button', { name: /select supplier/i }));
    expect(screen.getByRole('dialog').textContent).toContain('Alpha Supply');
    expect(screen.getByRole('dialog').textContent).toMatch(/does not execute/i);
  });

  it('builds information fields only from the approved safe schema', () => {
    state.action = action({
      action_type: 'information_request',
      allowed_decisions: ['submitted', 'unable'],
      safe_context: {
        requested_fields: [
          { id: 'device_model', label: 'Device model', required: true },
          { id: 'api_key', label: 'API key', required: true },
        ],
      },
    });
    render(<MemoryRouter initialEntries={['/app/human-actions/action-1']}><Routes><Route path="/app/human-actions/:actionId" element={<HumanActionDetailPage />} /></Routes></MemoryRouter>);
    fireEvent.click(screen.getByLabelText('submitted'));
    expect(screen.getByLabelText(/Device model/i)).toBeTruthy();
    expect(screen.queryByLabelText(/API key/i)).toBeNull();
  });

  it('renders completed actions as read-only', () => {
    state.action = action({
      status: 'resolved',
      can_respond: false,
      resolved_at: '2026-07-26T11:00:00Z',
      resolution_decision: 'approved',
      resolution_comment: 'Approved after review.',
    });
    render(<MemoryRouter initialEntries={['/app/human-actions/action-1']}><Routes><Route path="/app/human-actions/:actionId" element={<HumanActionDetailPage />} /></Routes></MemoryRouter>);
    expect(screen.queryByText('Choose your response')).toBeNull();
    expect(screen.getByText(/Final response: approved/i)).toBeTruthy();
    expect(screen.getByText(/Approved after review/i)).toBeTruthy();
  });
});
