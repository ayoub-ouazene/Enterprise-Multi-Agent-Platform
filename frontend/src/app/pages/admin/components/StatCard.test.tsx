import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatCard } from './StatCard';

describe('StatCard', () => {
  it('renders label, value and icon', () => {
    render(<StatCard label="Employees" value={42} icon={<span data-testid="icon" />} />);
    expect(screen.getByText('Employees')).toBeTruthy();
    expect(screen.getByText('42')).toBeTruthy();
    expect(screen.getByTestId('icon')).toBeTruthy();
  });

  it('renders string value', () => {
    render(<StatCard label="Status" value="Ready" icon={<span />} />);
    expect(screen.getByText('Ready')).toBeTruthy();
  });
});
