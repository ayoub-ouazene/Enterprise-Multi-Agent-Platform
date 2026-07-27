import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { ActorType, type AuthenticatedUser } from '../../api/types';
import { MobileNav } from './MobileNav';

vi.mock('../../api/hooks/useDepartments', () => ({ useDepartments: () => ({ data: [] }) }));

const user: AuthenticatedUser = {
  user_id: 'u1', company_id: 'c1', email: 'owner@example.com', actor_type: ActorType.COMPANY,
  employee_id: null, department_id: null, is_manager: false, permissions: [],
  company_active: true, onboarding_complete: true, must_change_password: false,
};

describe('mobile navigation drawer', () => {
  it('locks scrolling, focuses close, and closes with Escape', async () => {
    const onClose = vi.fn();
    render(<MemoryRouter><MobileNav isOpen onClose={onClose} user={user} /></MemoryRouter>);
    expect(document.body.style.overflow).toBe('hidden');
    const close = screen.getByRole('button', { name: 'Close navigation' });
    await waitFor(() => expect(document.activeElement).toBe(close));
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
