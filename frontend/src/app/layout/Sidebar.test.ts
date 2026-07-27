import { describe, expect, it } from 'vitest';
import { ActorType, type AuthenticatedUser } from '../../api/types';
import { buildNavigation } from './shell-utils';

function user(actor_type: ActorType, extra: Partial<AuthenticatedUser> = {}): AuthenticatedUser {
  return {
    user_id: 'user-1', company_id: 'company-1', email: 'person@example.com',
    actor_type, employee_id: null, department_id: null, is_manager: false,
    permissions: [], company_active: true, onboarding_complete: true,
    must_change_password: false, ...extra,
  };
}

const labels = (groups: ReturnType<typeof buildNavigation>) => groups.flatMap((group) => group.items.map((item) => item.label));

describe('role-aware navigation', () => {
  it('shows company administration but hides personal workspace', () => {
    const result = labels(buildNavigation(user(ActorType.COMPANY)));
    expect(result).toContain('Administration');
    expect(result).toContain('Human Actions');
    expect(result).not.toContain('My Workspace');
  });

  it('limits external users to requester-safe navigation', () => {
    const result = labels(buildNavigation(user(ActorType.EXTERNAL_USER)));
    expect(result).toContain('My Requests');
    expect(result).toContain('New Request');
    expect(result).not.toContain('Administration');
    expect(result).not.toContain('Human Actions');
  });

  it('adds only the authenticated manager department workspace', () => {
    const manager = user(ActorType.DEPARTMENT_MANAGER, { department_id: 'dept-it', is_manager: true });
    const result = labels(buildNavigation(manager, [
      { id: 'dept-it', name: 'Information Technology', department_type: 'it', is_active: true },
      { id: 'dept-hr', name: 'Human Resources', department_type: 'hr', is_active: true },
    ]));
    expect(result).toContain('Information Technology');
    expect(result).not.toContain('Human Resources');
  });
});
