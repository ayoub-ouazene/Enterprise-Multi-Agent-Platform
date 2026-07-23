
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface SseEventEnvelope {
  id?: string;
  event: string;
  data: Record<string, unknown>;
}

export interface DashboardSummary {
  activeRequests: number;
  pendingHumanActions: number;
  unreadNotifications: number;
  totalEmployees?: number;
  onboardingComplete?: boolean;
  policyReady?: boolean;
}
