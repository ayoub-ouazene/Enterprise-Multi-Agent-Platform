import { describe, it, expect } from 'vitest';
import { RequestPriority, RequestStatus } from '../../../api/types';
import type { BusinessRequestSummary } from '../../../api/types';
import { sortedByDepartmentPriority } from './DepartmentOverviewPage';

function makeRequest(partial: Partial<BusinessRequestSummary>): BusinessRequestSummary {
  return {
    id: 'test-id',
    request_type: 'test',
    title: 'Test',
    summary: '',
    status: RequestStatus.PROCESSING,
    current_stage: 'test',
    current_state_summary: '',
    priority: RequestPriority.NORMAL,
    owner_department_id: null,
    active_department_id: null,
    owner_department: null,
    active_department: null,
    requester_label: null,
    attention_required: false,
    pending_action_count: 0,
    can_cancel: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...partial,
  };
}

describe('sortedByDepartmentPriority', () => {
  const hr = { id: 'dept-hr', name: 'HR', department_type: 'hr' } as BusinessRequestSummary['owner_department'];
  const itDept = { id: 'dept-it', name: 'IT', department_type: 'it' } as BusinessRequestSummary['owner_department'];

  it('sorts attention-required before normal', () => {
    const items = [
      makeRequest({ attention_required: false, status: RequestStatus.WAITING_FOR_HUMAN_ACTION, owner_department: hr }),
      makeRequest({ attention_required: true, status: RequestStatus.PROCESSING, owner_department: hr }),
    ];
    const result = sortedByDepartmentPriority(items, 'hr');
    expect(result[0].attention_required).toBe(true);
  });

  it('sorts owned before collaborating before other', () => {
    const items = [
      makeRequest({ owner_department: itDept, active_department: null }),
      makeRequest({ owner_department: null, active_department: itDept }),
      makeRequest({ owner_department: hr, active_department: null }),
    ];
    const result = sortedByDepartmentPriority(items, 'it');
    expect(result[0].owner_department?.department_type).toBe('it');
    expect(result[1].active_department?.department_type).toBe('it');
    expect(result[2].owner_department?.department_type).toBe('hr');
  });

  it('sorts by status weight after relation', () => {
    const items = [
      makeRequest({ owner_department: hr, status: RequestStatus.UNDER_REVIEW }),
      makeRequest({ owner_department: hr, status: RequestStatus.CREATED }),
      makeRequest({ owner_department: hr, status: RequestStatus.WAITING_FOR_HUMAN_ACTION }),
    ];
    const result = sortedByDepartmentPriority(items, 'hr');
    expect(result[0].status).toBe(RequestStatus.WAITING_FOR_HUMAN_ACTION);
    expect(result[1].status).toBe(RequestStatus.UNDER_REVIEW);
    expect(result[2].status).toBe(RequestStatus.CREATED);
  });

  it('sorts by priority within same status and relation', () => {
    const items = [
      makeRequest({ owner_department: hr, status: RequestStatus.PROCESSING, priority: RequestPriority.LOW }),
      makeRequest({ owner_department: hr, status: RequestStatus.PROCESSING, priority: RequestPriority.URGENT }),
      makeRequest({ owner_department: hr, status: RequestStatus.PROCESSING, priority: RequestPriority.HIGH }),
    ];
    const result = sortedByDepartmentPriority(items, 'hr');
    expect(result[0].priority).toBe(RequestPriority.URGENT);
    expect(result[1].priority).toBe(RequestPriority.HIGH);
    expect(result[2].priority).toBe(RequestPriority.LOW);
  });

  it('does not mutate the original array', () => {
    const items = [
      makeRequest({ attention_required: false, owner_department: hr }),
      makeRequest({ attention_required: true, owner_department: hr }),
    ];
    sortedByDepartmentPriority(items, 'hr');
    expect(items[0].attention_required).toBe(false);
    expect(items[1].attention_required).toBe(true);
  });
});
