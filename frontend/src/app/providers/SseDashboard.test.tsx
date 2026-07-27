import { QueryClient } from '@tanstack/react-query';
import { act, render } from '@testing-library/react';
import { useEffect } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuthStore } from '../../auth/store';
import { SseProvider, useSseConnection } from './SseProvider';

class FakeEventSource {
  static current: FakeEventSource;
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  listeners = new Map<string, (event: MessageEvent) => void>();
  constructor(url: string) {
    void url;
    FakeEventSource.current = this;
  }
  addEventListener(type: string, listener: EventListenerOrEventListenerObject) {
    this.listeners.set(type, listener as (event: MessageEvent) => void);
  }
  emit(type: string, data: Record<string, unknown>, id = '') {
    this.listeners.get(type)?.(new MessageEvent(type, { data: JSON.stringify(data), lastEventId: id }));
  }
  close() {}
}

function Harness() {
  const { connect } = useSseConnection();
  useEffect(() => connect('/events'), [connect]);
  return null;
}

describe('dashboard SSE invalidation', () => {
  beforeEach(() => {
    vi.stubGlobal('EventSource', FakeEventSource);
    useAuthStore.getState().setTokens({
      access_token: 'test-token', refresh_token: 'refresh',
      access_token_expires_in: 60, refresh_token_expires_in: 120,
    });
  });

  it('refreshes dashboard for request events but not heartbeats', () => {
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    render(<SseProvider queryClient={client}><Harness /></SseProvider>);
    act(() => FakeEventSource.current.onmessage?.(new MessageEvent('message', { data: JSON.stringify({ type: 'heartbeat' }) })));
    expect(invalidate).not.toHaveBeenCalledWith(expect.objectContaining({ queryKey: ['dashboard'] }));
    act(() => FakeEventSource.current.onmessage?.(new MessageEvent('message', { data: JSON.stringify({ entity: 'request', request_id: 'r1' }) })));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['dashboard'] });
  });

  it('refreshes only the related request projection and deduplicates workflow events', () => {
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    render(<SseProvider queryClient={client}><Harness /></SseProvider>);
    act(() => FakeEventSource.current.emit('workflow_event', { request_id: 'request-1', event_type: 'stage_started' }, 'event-7'));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['request', 'request-1'] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['workflow-events', 'request-1'] });
    const callsAfterFirstEvent = invalidate.mock.calls.length;
    act(() => FakeEventSource.current.emit('workflow_event', { request_id: 'request-1', event_type: 'stage_started' }, 'event-7'));
    expect(invalidate.mock.calls.length).toBe(callsAfterFirstEvent);
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: ['request', 'unrelated-request'] });
  });

  it('targets HumanAction, inbox, notification, and related-request projections', () => {
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    render(<SseProvider queryClient={client}><Harness /></SseProvider>);
    act(() => FakeEventSource.current.onmessage?.(new MessageEvent('message', {
      data: JSON.stringify({ entity: 'human_action', action_id: 'action-1', request_id: 'request-1' }),
    })));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['human-action', 'action-1'] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['human-actions'] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['notifications', 'unread'] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['request', 'request-1'] });
  });

  it('refreshes the inbox when an action-required notification arrives', () => {
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    render(<SseProvider queryClient={client}><Harness /></SseProvider>);
    act(() => FakeEventSource.current.emit('notification', {
      notification_type: 'human_action_required',
      request_id: 'request-1',
    }, 'notification-1'));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['human-actions'] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['notifications'] });
  });

  it('targets the changed administration resource and ignores unrelated caches', () => {
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    render(<SseProvider queryClient={client}><Harness /></SseProvider>);
    act(() => FakeEventSource.current.onmessage?.(new MessageEvent('message', {
      data: JSON.stringify({ entity: 'asset', id: 'asset-1' }),
    })));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['admin', 'assets'] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['admin', 'summary'] });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: ['admin', 'budgets'] });
  });
});
