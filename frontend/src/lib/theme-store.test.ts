import { beforeEach, describe, expect, it, vi } from 'vitest';
import { THEME_STORAGE_KEY, useThemeStore } from './theme-store';

describe('theme preference', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.className = '';
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({
      matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn(),
    }));
  });

  it('persists light, dark, and system preferences', () => {
    useThemeStore.getState().setTheme('dark');
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    useThemeStore.getState().setTheme('system');
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('system');
    expect(useThemeStore.getState().resolvedTheme).toBe('dark');
  });
});
