import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ValidationSummary } from './components/ValidationSummary';
import { ActivationModal } from './components/ActivationModal';

describe('secure onboarding experience', () => {
  it('renders only allowlisted preview fields and password indicators', () => {
    render(<MemoryRouter><ValidationSummary result={{
      import_job_id: 'job-1', import_type: 'employees', original_filename: 'employees.csv',
      atomic: true, total_rows: 1, valid_rows: 1, invalid_rows: 0, can_confirm: true,
      rows: [{ row_number: 1, status: 'valid', errors: [], preview: {
        email: 'safe@example.com', password_provided: true,
        temporary_password: 'NeverRenderThis!', _password_hash: 'NeverRenderHash',
        secret_note: 'NeverRenderSecret',
      } }],
    }} onConfirm={vi.fn()} onCancel={vi.fn()} /></MemoryRouter>);
    expect(screen.getByText('safe@example.com')).toBeTruthy();
    expect(screen.getByText('Yes')).toBeTruthy();
    expect(document.body.textContent).not.toContain('NeverRender');
    expect(screen.getByText(/Atomic import/i)).toBeTruthy();
  });

  it('requires deliberate activation confirmation', () => {
    const confirm = vi.fn();
    render(<MemoryRouter><ActivationModal open onClose={vi.fn()} onConfirm={confirm} isActivating={false} /></MemoryRouter>);
    expect((screen.getByRole('button', { name: 'Activate Company' }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Activate Company' }));
    expect(confirm).toHaveBeenCalledTimes(1);
  });
});
