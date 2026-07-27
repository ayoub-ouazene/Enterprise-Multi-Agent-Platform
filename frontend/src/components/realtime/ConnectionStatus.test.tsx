import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ConnectionStatus } from './ConnectionStatus';

const state = vi.hoisted(() => ({ connected: false }));
vi.mock('../../app/providers/SseProvider', () => ({
  useSseConnection: () => ({ connected: state.connected }),
}));

describe('connection indicator', () => {
  it('presents disconnected state without blocking the application', () => {
    state.connected = false;
    render(<ConnectionStatus />);
    expect(screen.getByRole('status').textContent).toContain('Offline');
  });

  it('presents the live state', () => {
    state.connected = true;
    render(<ConnectionStatus />);
    expect(screen.getByRole('status').textContent).toContain('Live');
  });
});
