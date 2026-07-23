import { describe, it, expect } from 'vitest';
import { formatDate, relativeTime, groupByDate } from './formatters';

describe('formatters', () => {
  it('formatDate returns a string', () => {
    const result = formatDate('2024-03-15T10:00:00Z');
    expect(typeof result).toBe('string');
    expect(result.length).toBeGreaterThan(0);
  });

  it('relativeTime returns a string', () => {
    const now = new Date().toISOString();
    expect(typeof relativeTime(now)).toBe('string');
  });

  it('groupByDate groups items', () => {
    const items = [
      { created_at: new Date().toISOString() },
      { created_at: new Date().toISOString() },
      { created_at: new Date(Date.now() - 86400000).toISOString() },
    ];
    const groups = groupByDate(items);
    expect(groups.length).toBeGreaterThanOrEqual(1);
    expect(groups[0].items.length).toBeGreaterThanOrEqual(1);
    expect(groups[0].label).toBeTruthy();
  });
});
