import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiErrorException } from './client';
import { useAuthStore } from '../auth/store';


describe('authentication API client behavior', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
    useAuthStore.getState().logout();
  });

  it('does not attempt token refresh for a login 401', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ detail: 'Invalid authentication credentials' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      api.post(
        '/auth/login',
        { company_slug: 'acme', email: 'user@example.com', password: 'incorrect password' },
        { skipAuth: true },
      ),
    ).rejects.toMatchObject({
      error: {
        status: 401,
        code: 'UNAUTHORIZED',
      },
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('preserves a safe registration conflict message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ detail: 'Company workspace already exists' }),
        { status: 409, headers: { 'Content-Type': 'application/json' } },
      ),
    ));

    try {
      await api.post('/companies/register', {}, { skipAuth: true });
      throw new Error('Expected registration to fail');
    } catch (error) {
      expect(error).toBeInstanceOf(ApiErrorException);
      expect((error as ApiErrorException).error.message).toBe('Company workspace already exists');
    }
  });

  it('classifies an unreachable backend as a network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    await expect(
      api.get('/health', { skipAuth: true }),
    ).rejects.toMatchObject({
      error: {
        status: 0,
        code: 'NETWORK_ERROR',
      },
    });
  });
});
