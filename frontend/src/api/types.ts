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
  CREATED = 'created',
  ROUTING = 'routing',
  PROCESSING = 'processing',
  WAITING_FOR_DEPARTMENT = 'waiting_for_department',
  WAITING_FOR_HUMAN_APPROVAL = 'waiting_for_human_approval',
  WAITING_FOR_HUMAN_ACTION = 'waiting_for_human_action',
  UNDER_REVIEW = 'under_review',
  COMPLETED = 'completed',
  REJECTED = 'rejected',
  CANCELLED = 'cancelled',
  FAILED = 'failed',
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
  workflow_state: Record<string, unknown>;
}

export enum WorkflowEventType {
  REQUEST_CREATED = 'request_created',
  ROUTING_STARTED = 'routing_started',
  REQUEST_ROUTED = 'request_routed',
  STAGE_STARTED = 'stage_started',
  STAGE_COMPLETED = 'stage_completed',
  DEPARTMENT_COLLABORATION_STARTED = 'department_collaboration_started',
  DEPARTMENT_COLLABORATION_COMPLETED = 'department_collaboration_completed',
  WAITING_FOR_HUMAN_APPROVAL = 'waiting_for_human_approval',
  WAITING_FOR_HUMAN_ACTION = 'waiting_for_human_action',
  REVIEW_STARTED = 'review_started',
  REVIEW_COMPLETED = 'review_completed',
  REQUEST_RESUMED = 'request_resumed',
  REQUEST_COMPLETED = 'request_completed',
  REQUEST_REJECTED = 'request_rejected',
  REQUEST_CANCELLED = 'request_cancelled',
  REQUEST_FAILED = 'request_failed',
  FAILURE_RECORDED = 'failure_recorded',
  CAPABILITY_GAP_DETECTED = 'capability_gap_detected',
}

export interface WorkflowEvent {
  id: UUID;
  request_id: UUID;
  event_type: WorkflowEventType;
  stage: string | null;
  title: string;
  message: string;
  actor_label: string;
  department_id: UUID | null;
  event_data: Record<string, unknown>;
  sequence_number: number;
  created_at: string;
}

export interface WorkflowControlResponse {
  request_id: UUID;
  status: RequestStatus;
  current_stage: string;
  owner_department_id: UUID | null;
  active_department_id: UUID | null;
  state_version: number;
  message_category: string | null;
  owner_department: string | null;
  needs_clarification: boolean;
  clarification_question: string | null;
  response: string | null;
}

export interface HumanActionSubmitResponse {
  id: UUID;
  status: string;
  resolved_at: string | null;
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

// ---------------------------------------------------------------------------
// Onboarding wizard extensions (mirrors backend schemas)
// ---------------------------------------------------------------------------

export interface OnboardingStatusItem {
  requirement: string;
  satisfied: boolean;
  details: string | null;
}

export interface OnboardingStatusDetailed {
  company_id: UUID;
  can_activate: boolean;
  is_active: boolean;
  items: OnboardingStatusItem[];
}

export interface RowValidationResult {
  row_number: number;
  status: string; // "valid" | "invalid"
  errors: string[];
  preview: Record<string, unknown> | null;
}

export interface ImportValidateResponse {
  import_job_id: UUID;
  import_type: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  can_confirm: boolean;
  rows: RowValidationResult[];
}

export interface ImportConfirmResponse {
  import_job_id: UUID;
  status: string;
  processed_rows: number;
  errors: string[] | null;
}

export interface TemplateColumn {
  name: string;
  required: boolean;
  description: string | null;
}

export interface ImportTemplateResponse {
  import_type: string;
  columns: TemplateColumn[];
  csv_header: string;
}

export interface ImportJobDetailed {
  id: UUID;
  company_id: UUID;
  import_type: string;
  status: string;
  original_filename: string;
  uploaded_by_user_id: UUID;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  processed_rows: number;
  error_summary: string | null;
  checksum: string;
  idempotency_key: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
}

export interface DocumentUploadPayload {
  file: File;
  title: string;
  document_type: string;
  department_scope: string[];
  access_scope: string;
  effective_date?: string | null;
  custom_metadata?: Record<string, unknown>;
}

export interface DocumentListResponse {
  id: UUID;
  title: string;
  document_type: string;
  ingestion_status: string;
  is_active: boolean;
  department_scope: string[];
  tags: string[];
  created_at: string;
}

export interface PolicyReadinessResponse {
  total_documents: number;
  ingested_active_policies: number;
  department_coverage: Record<string, boolean>;
  ready: boolean;
}

export interface AdminDepartmentResponse {
  id: UUID;
  name: string;
  department_type: string;
  is_active: boolean;
  custom_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AdminEmployeeResponse {
  id: UUID;
  user_id: UUID | null;
  employee_code: string;
  job_title: string | null;
  department_id: UUID | null;
  hire_date: string | null;
  manager_employee_id: UUID | null;
  employment_status: string;
  custom_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
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
  assigned_user_id: UUID | null;
  assigned_role: string | null;
  decision_package: Record<string, unknown>;
  response: Record<string, unknown>;
  due_date: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
  // Computed fields
  allowed_decisions: string[];
  can_respond: boolean;
  request_title: string | null;
  request_status: string | null;
}

export type HumanActionDetail = HumanActionSummary;

export interface AdminSummary {
  totalEmployees: number;
  totalDepartments: number;
  activeRequests: number;
  pendingHumanActions: number;
  policyReadiness: boolean;
  capabilityGaps: number;
}

// ---------------------------------------------------------------------------
// Admin dashboard types (Step 29)
// ---------------------------------------------------------------------------

export interface AdminSummaryResponse {
  total_employees: number;
  total_departments: number;
  active_requests: number;
  pending_human_actions: number;
  policy_ready: boolean;
}

export interface AdminCompanyProfile {
  id: UUID;
  name: string;
  slug: string;
  is_active: boolean;
  custom_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AdminAssetResponse {
  id: UUID;
  asset_code: string;
  asset_type: string;
  brand: string;
  model: string;
  serial_number: string | null;
  status: string;
  location: string | null;
  custom_data: Record<string, unknown>;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface AdminSoftwareCatalogResponse {
  id: UUID;
  name: string;
  access_type: string;
  requires_manager_approval: boolean;
  requires_it_approval: boolean;
  license_limited: boolean;
  available_license_count: number | null;
  is_active: boolean;
  custom_data: Record<string, unknown>;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface AdminBudgetResponse {
  id: UUID;
  department_id: UUID | null;
  name: string;
  budget_type: string;
  currency: string;
  period_start: string;
  period_end: string;
  allocated_amount: string;
  reserved_amount: string;
  committed_amount: string;
  spent_amount: string;
  available_amount: string;
  status: string;
  approval_threshold: string | null;
  custom_data: Record<string, unknown>;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface AdminHolidayResponse {
  id: UUID;
  holiday_date: string;
  name: string;
  is_paid: boolean;
  custom_data: Record<string, unknown>;
}

export interface AdminStaffingRuleResponse {
  id: UUID;
  department_id: UUID;
  minimum_active_employees: number;
  effective_from: string;
  effective_to: string | null;
  is_active: boolean;
  custom_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AdminSupplierResponse {
  id: UUID;
  name: string;
  contact_person: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  website: string | null;
  is_active: boolean;
  custom_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}
