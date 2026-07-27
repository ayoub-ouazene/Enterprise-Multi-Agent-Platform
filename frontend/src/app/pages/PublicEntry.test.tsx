import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LandingPage } from './LandingPage';
import { SignupPage } from './SignupPage';
import { QueryProvider } from '../providers/QueryProvider';
import '../../test/setup';


describe('public entry pages', () => {
  it('offers distinct Company registration and existing-account login actions', () => {
    render(<MemoryRouter><LandingPage /></MemoryRouter>);
    expect(screen.getAllByRole('link', { name: /create (company )?workspace/i })[0].getAttribute('href')).toBe('/signup');
    expect(screen.getAllByRole('link', { name: /^sign in$/i })[0].getAttribute('href')).toBe('/login');
    expect(screen.getByRole('heading', { level: 1, name: /move enterprise requests/i })).toBeTruthy();
  });

  it('explains that non-Company roles are provisioned separately', () => {
    render(
      <QueryProvider>
        <MemoryRouter><SignupPage /></MemoryRouter>
      </QueryProvider>,
    );
    expect(screen.getByText(/employee, manager, and external requester accounts are provisioned separately/i)).toBeTruthy();
  });

  it('provides a keyboard-accessible mobile public navigation', () => {
    render(<MemoryRouter><LandingPage /></MemoryRouter>);
    const menu = screen.getByRole('button', { name: /open navigation menu/i });
    menu.focus();
    expect(document.activeElement).toBe(menu);
    fireEvent.click(menu);
    expect(screen.getByRole('navigation', { name: /mobile public navigation/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /close navigation menu/i }).getAttribute('aria-expanded')).toBe('true');
  });
});
