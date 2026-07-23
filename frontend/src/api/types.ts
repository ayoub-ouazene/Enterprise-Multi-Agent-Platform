export type UUID = string;

export enum ActorType {
  COMPANY = 'company',
  DEPARTMENT_MANAGER = 'department_manager',
  EMPLOYEE = 'employee',
  EXTERNAL_USER = 'external_user',
}

export interface AuthenticatedUser {
  user_id: UUID;
  company_id: UUID;
  email: string;
  actor_type: ActorType;
  employee_id: UUID | null;
  department_id: UUID | null;
  is_manager: boolean;
  permissions: string[];
}

export interface Company {
  id: UUID;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Department {
  id: UUID;
  name: string;
  department_type: string;
  is_active: boolean;
}

export enum RequestStatus {
  DRAFT = 'draft',
  SUBMITTED = 'submitted',
  IN_PROGRESS = 'in_progress',
  PENDING_APPROVAL = 'pending_approval',
  PENDING_ACTION = 'pending_action',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
  FAILED = 'failed',
  REJECTED = 'rejected',
}

export enum RequestPriority {
  LOW = 'low',
  NORMAL = 'normal',
  HIGH = 'high',
  URGENT = 'urgent',
}

export interface BusinessRequestSummary {
  id: UUID;
  request_type: string;
  title: string;
  summary: string;
  status: RequestStatus;
  current_stage: string;
  priority: RequestPriority;
  owner_department_id: UUID | null;
  active_department_id: UUID | null;
  created_at: string;
  updated_at: string;
}

export interface BusinessRequestDetail extends BusinessRequestSummary {
  requester_user_id: UUID;
  requester_employee_id: UUID | null;
  final_decision: string | null;
  final_reason: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  failed_at: string | null;
}

export enum NotificationType {
  REQUEST_UPDATE = 'request_update',
  APPROVAL_REQUIRED = 'approval_required',
  ACTION_REQUIRED = 'action_required',
  SYSTEM = 'system',
  MENTION = 'mention',
}

export enum NotificationSeverity {
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  SUCCESS = 'success',
}

export interface Notification {
  id: UUID;
  request_id: UUID | null;
  notification_type: NotificationType;
  title: string;
  message: string;
  severity: NotificationSeverity;
  action_required: boolean;
  action_type: string | null;
  action_url: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
  expires_at: string | null;
}

export interface OnboardingStatus {
  company_id: UUID;
  is_active: boolean;
  onboarding_complete: boolean;
  can_activate: boolean;
  missing_steps: string[];
  last_import_job_id: UUID | null;
  last_import_at: string | null;
}

export interface ImportJob {
  id: UUID;
  import_type: string;
  status: string;
  row_count: number | null;
  processed_count: number;
  created_at: string;
  completed_at: string | null;
}

export interface HumanActionSummary {
  id: UUID;
  request_id: UUID;
  action_type: string;
  title: string;
  description: string;
  status: string;
  due_date: string | null;
  created_at: string;
}

export interface AdminSummary {
  totalEmployees: number;
  totalDepartments: number;
  activeRequests: number;
  pendingHumanActions: number;
  policyReadiness: boolean;
  capabilityGaps: number;
}
