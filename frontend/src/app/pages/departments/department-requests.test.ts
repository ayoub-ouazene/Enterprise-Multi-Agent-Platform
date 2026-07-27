import { describe, it, expect } from 'vitest';
import type { BusinessRequestSummary } from '../../../api/types';

function requestRelation(request: Pick<BusinessRequestSummary, 'owner_department_id' | 'active_department_id'>, departmentId: string | null) {
  if (!departmentId) return 'unknown' as const;
  if (request.owner_department_id === departmentId) return 'owned' as const;
  if (request.active_department_id === departmentId) return 'collaborating' as const;
  return 'other' as const;
}

function dueUrgency(dueDate: string | null): 'critical' | 'warning' | 'normal' {
  if (!dueDate) return 'normal';
  const diff = new Date(dueDate).getTime() - Date.now();
  const hours = diff / (1000 * 60 * 60);
  if (hours < 0) return 'critical';
  if (hours < 24) return 'warning';
  return 'normal';
}

describe('requestRelation', () => {
  it('identifies owned requests', () => {
    const request = { owner_department_id: 'd1', active_department_id: null };
    expect(requestRelation(request, 'd1')).toBe('owned');
  });

  it('identifies collaborating requests', () => {
    const request = { owner_department_id: 'd1', active_department_id: 'd2' };
    expect(requestRelation(request, 'd2')).toBe('collaborating');
  });

  it('identifies other requests', () => {
    const request = { owner_department_id: 'd1', active_department_id: null };
    expect(requestRelation(request, 'd2')).toBe('other');
  });

  it('returns unknown when departmentId is null', () => {
    expect(requestRelation({ owner_department_id: 'd1', active_department_id: null }, null)).toBe('unknown');
  });
});

describe('dueUrgency', () => {
  it('returns critical when overdue', () => {
    const past = new Date(Date.now() - 1000).toISOString();
    expect(dueUrgency(past)).toBe('critical');
  });

  it('returns warning when due within 24 hours', () => {
    const near = new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString();
    expect(dueUrgency(near)).toBe('warning');
  });

  it('returns normal when due beyond 24 hours', () => {
    const far = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString();
    expect(dueUrgency(far)).toBe('normal');
  });

  it('returns normal when no due date', () => {
    expect(dueUrgency(null)).toBe('normal');
  });
});
