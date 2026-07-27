import { beforeEach, describe, expect, it } from 'vitest';
import { getInitialSidebarCollapsed, persistSidebarCollapsed, SIDEBAR_KEY } from './shell-utils';

describe('desktop sidebar preference', () => {
  beforeEach(() => localStorage.clear());

  it('persists collapse state without changing route content', () => {
    expect(getInitialSidebarCollapsed()).toBe(false);
    persistSidebarCollapsed(true);
    expect(localStorage.getItem(SIDEBAR_KEY)).toBe('true');
    expect(getInitialSidebarCollapsed()).toBe(true);
  });
});
