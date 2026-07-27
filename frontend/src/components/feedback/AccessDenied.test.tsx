import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AccessDenied } from './AccessDenied';

describe('access denied state', () => {
  it('shows a safe explanation and recovery action', () => {
    render(<MemoryRouter><AccessDenied /></MemoryRouter>);
    expect(screen.getByText('Access Denied')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Go to Dashboard' })).toBeTruthy();
    expect(document.body.textContent).not.toContain('stack');
  });
});
