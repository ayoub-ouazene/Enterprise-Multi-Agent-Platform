import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from './StatusBadge';

describe('StatusBadge', () => {
  it.each([
    ['success', 'Active'],
    ['warning', 'Pending'],
    ['error', 'Failed'],
    ['info', 'Processing'],
    ['neutral', 'Inactive'],
  ] as const)('renders %s badge with text %s', (status, text) => {
    render(<StatusBadge status={status}>{text}</StatusBadge>);
    expect(screen.getByText(text)).toBeTruthy();
  });
});
