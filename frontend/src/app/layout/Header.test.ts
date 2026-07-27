import { describe, expect, it, vi } from 'vitest';
import { queryClient } from '../providers/QueryProvider';
import { clearSensitiveSession } from './session-cleanup';

describe('authenticated session cleanup', () => {
  it('clears user state and all cached server data on logout', () => {
    const logout = vi.fn();
    queryClient.setQueryData(['private', 'company-1'], { secret: 'cached' });
    clearSensitiveSession(logout);
    expect(logout).toHaveBeenCalledOnce();
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
  });
});
