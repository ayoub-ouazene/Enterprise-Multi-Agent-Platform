import { describe, it, expect } from 'vitest';
import {
  getRequestStatusMeta,
  getHumanActionStatusMeta,
  getNotificationSeverityMeta,
  statusCategoryStyles,
} from './status';

describe('status utilities', () => {
  it('maps request statuses with labels', () => {
    expect(getRequestStatusMeta('processing').label).toBe('Processing');
    expect(getRequestStatusMeta('completed').category).toBe('success');
    expect(getRequestStatusMeta('waiting_for_human_approval').category).toBe('pending');
    expect(getRequestStatusMeta('failed').category).toBe('failed');
    expect(getRequestStatusMeta('unknown').label).toBe('unknown');
    expect(getRequestStatusMeta('unknown').category).toBe('neutral');
  });

  it('maps human action statuses', () => {
    expect(getHumanActionStatusMeta('pending').label).toBe('Pending');
    expect(getHumanActionStatusMeta('overdue').category).toBe('attention');
    expect(getHumanActionStatusMeta('resolved').category).toBe('success');
    expect(getHumanActionStatusMeta('cancelled').category).toBe('cancelled');
  });

  it('maps notification severities', () => {
    expect(getNotificationSeverityMeta('error').category).toBe('failed');
    expect(getNotificationSeverityMeta('warning').category).toBe('attention');
    expect(getNotificationSeverityMeta('success').category).toBe('success');
    expect(getNotificationSeverityMeta('info').category).toBe('neutral');
  });

  it('provides styles for every category', () => {
    const categories = ['neutral', 'info', 'inProgress', 'pending', 'attention', 'success', 'completed', 'failed', 'cancelled'] as const;
    for (const cat of categories) {
      expect(statusCategoryStyles[cat]).toBeDefined();
      expect(statusCategoryStyles[cat].badgeClass).toContain('bg-');
      expect(statusCategoryStyles[cat].dotClass).toContain('bg-');
    }
  });
});
