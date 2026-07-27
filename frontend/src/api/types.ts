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
  company_active: boolean;
  onboarding_complete: boolean;
  must_change_password: boolean;
}

export interface DashboardMetric {
  key: string;
  label: string;
  value: number;
  detail: string | null;
  status: 'neutral' | 'info' | 'success' | 'warning' | 'danger';
  href: string | null;
}

export interface DashboardAttentionItem {
  id: string;
  severity: string;
  title: string;
  explanation: string;
  resource_type: string;
  resource_id: UUID | null;
  action_label: string;
  action_url: string;
  occurred_at: string | null;
  due_at: string | null;
}

export interface DashboardRequestItem {
  id: UUID;
  title: string;
  status: string;
  priority: string;
  current_stage: string;
  owner_department: string | null;
  action_required: boolean;
  updated_at: string;
}

export interface DashboardActionItem {
  id: UUID;
  request_id: UUID;
  title: string;
  action_type: string;
  due_at: string | null;
  created_at: string;
}

export interface DashboardActivityItem {
  id: UUID;
  title: string;
  message: string;
  severity: string;
  resource_url: string | null;
  occurred_at: string;
}

export interface DashboardReadinessItem {
  key: string;
  label: string;
  ready: boolean;
  detail: string | null;
}

export interface DashboardDepartmentItem {
  id: UUID;
  name: string;
  department_type: string;
  enabled: boolean;
  manager_label: string | null;
  ready: boolean;
  active_requests: number;
  pending_actions: number;
}

export interface DashboardResponse {
  role: ActorType;
  identity: {
    company_name: string;
    company_active: boolean;
    account_label: string;
    department_name: string | null;
    department_type: string | null;
  };
  metrics: DashboardMetric[];
  attention: DashboardAttentionItem[];
  active_requests: DashboardRequestItem[];
  completed_requests: DashboardRequestItem[];
  pending_actions: DashboardActionItem[];
  activity: DashboardActivityItem[];
  readiness: DashboardReadinessItem[];
  departments: DashboardDepartmentItem[];
  generated_at: string;
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
  current_state_summary: string;
  priority: RequestPriority;
  owner_department_id: UUID | null;
  active_department_id: UUID | null;
  owner_department: RequestDepartment | null;
  active_department: RequestDepartment | null;
  requester_user_id?: UUID | null;
  requester_label: string | null;
  attention_required: boolean;
  pending_action_count: number;
  can_cancel: boolean;
  created_at: string;
  updated_at: string;
}

export interface RequestDepartment {
  id: UUID;
  name: string;
  department_type: string;
}

export interface ConnectedHumanAction {
  id: UUID;
  title: string;
  action_type: string;
  status: string;
  due_at: string | null;
  assigned_role: string | null;
  can_respond: boolean;
  action_url: string | null;
}

export interface RequestClarification {
  question: string;
  number: number;
  maximum: number;
}

export interface RequestSourceReference {
  document_id: UUID | null;
  title: string;
  version: string | null;
  section: string | null;
  scope: string | null;
}

export interface RequestFinalResult {
  title: string;
  summary: string;
  limitations: string[];
  next_steps: string[];
  sources: RequestSourceReference[];
}

export interface BusinessRequestDetail extends BusinessRequestSummary {
  requester_employee_id: UUID | null;
  final_decision: string | null;
  final_reason: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  failed_at: string | null;
  clarification: RequestClarification | null;
  collaboration_summary: string | null;
  quality_check_summary: string | null;
  failure_summary: string | null;
  final_result: RequestFinalResult | null;
  connected_actions: ConnectedHumanAction[];
  allowed_actions: string[];
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
  title: string;
  message: string;
  actor_label: string;
  department_id: UUID | null;
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

export interface OnboardingManagerCandidate {
  id: UUID;
  department_id: UUID;
  employee_code: string;
  job_title: string | null;
  is_current_manager: boolean;
}

export interface OnboardingManagerCoverage {
  department_id: UUID;
  department_name: string;
  department_type: string;
  manager: OnboardingManagerCandidate | null;
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
  original_filename: string;
  atomic: boolean;
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
  email: string | null;
  account_active: boolean;
  must_change_password: boolean;
  actor_type: string | null;
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
  status: string;
  assigned_role: string | null;
  due_date: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
  // Computed fields
  allowed_decisions: string[];
  can_respond: boolean;
  request_title: string | null;
  request_status: string | null;
  requesting_department: string | null;
}

export interface SafeActionHistoryItem {
  event: 'created' | 'resolved' | 'cancelled';
  title: string;
  description: string;
  occurred_at: string;
}

export interface HumanActionDetail extends HumanActionSummary {
  description: string;
  safe_context: Record<string, unknown>;
  resolution_decision: string | null;
  resolution_comment: string | null;
  related_request: {
    id: UUID;
    title: string;
    status: string;
    owner_department: string | null;
  };
  history: SafeActionHistoryItem[];
}

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
  assigned_employee_id: UUID | null;
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

// ---------------------------------------------------------------------------
// Assistant / Platform chat (Step 31)
// ---------------------------------------------------------------------------

export enum RouterMessageCategory {
  PLATFORM_QUESTION = 'platform_question',
  DEPARTMENT_QUESTION = 'department_question',
  BUSINESS_REQUEST = 'business_request',
  UNCLEAR = 'unclear',
  UNSUPPORTED = 'unsupported',
}

export interface AssistantMessageRequest {
  message: string;
  request_id: UUID | null;
}

export interface AssistantMessageResponse {
  message_category: RouterMessageCategory;
  owner_department: string | null;
  request_id: UUID | null;
  request_status: RequestStatus | null;
  needs_clarification: boolean;
  clarification_question: string | null;
  response: string;
  request_type: string | null;
  short_summary: string | null;
}

// ---------------------------------------------------------------------------
// Employee self-service types (Step 32)
// ---------------------------------------------------------------------------

export interface LeaveBalanceResponse {
  id: UUID;
  employee_id: UUID;
  leave_type: string;
  year: number;
  allocated_days: string;
  used_days: string;
  reserved_days: string;
  remaining_days: string;
  created_at: string;
  updated_at: string;
}

export interface LeaveRequestResponse {
  request_id: UUID;
  employee_id: UUID;
  leave_type: string;
  start_date: string;
  end_date: string;
  requested_days: string;
  eligibility_status: string;
  balance_status: string;
  staffing_status: string;
  approval_required: boolean;
  approval_status: string;
  decision: string;
  decision_reason: string | null;
  reserved_days: string;
  created_at: string;
  updated_at: string;
  decided_at: string | null;
  cancelled_at: string | null;
}

// ---------------------------------------------------------------------------
// Department workspace types (Step 30)
// ---------------------------------------------------------------------------

export interface DepartmentStatsResponse {
  active_requests: number;
  pending_human_actions: number;
  collaborations_ongoing: number;
  completed_today: number;
}

export interface DepartmentReadinessItem {
  name: string;
  ready: boolean;
  detail: string | null;
}

export interface DepartmentReadinessResponse {
  department_type: string;
  overall_ready: boolean;
  items: DepartmentReadinessItem[];
}

export interface DepartmentActivityResponse {
  id: UUID;
  request_id: UUID;
  event_type: string;
  title: string;
  message: string;
  actor_label: string;
  created_at: string;
}

export interface DepartmentOperationalField {
  label: string;
  value: string;
  emphasis: 'default' | 'positive' | 'warning' | 'critical';
}

export interface DepartmentOperationalRecord {
  id: UUID;
  request_id: UUID | null;
  record_type: string;
  title: string;
  summary: string | null;
  status: string;
  fields: DepartmentOperationalField[];
  action_url: string | null;
  updated_at: string | null;
}

// ---------------------------------------------------------------------------
// Failure management (Step 33)
// ---------------------------------------------------------------------------

export enum FailureType {
  TOOL_FAILURE = 'tool_failure',
  DATABASE_FAILURE = 'database_failure',
  RETRIEVAL_FAILURE = 'retrieval_failure',
  EXTERNAL_SERVICE_FAILURE = 'external_service_failure',
  VALIDATION_FAILURE = 'validation_failure',
  AUTHORIZATION_FAILURE = 'authorization_failure',
  WORKFLOW_FAILURE = 'workflow_failure',
  CONFIGURATION_FAILURE = 'configuration_failure',
  UNEXPECTED_FAILURE = 'unexpected_failure',
}

export enum FailureSource {
  API = 'api',
  SERVICE = 'service',
  REPOSITORY = 'repository',
  TOOL = 'tool',
  WORKFLOW = 'workflow',
  RAG = 'rag',
  LLM = 'llm',
  EXTERNAL_SERVICE = 'external_service',
  SYSTEM = 'system',
}

export interface FailureDetailResponse {
  id: UUID;
  request_id: UUID | null;
  department_id: UUID | null;
  failure_type: FailureType;
  failure_source: FailureSource;
  failed_operation: string;
  internal_message: string;
  safe_message: string;
  error_code: string | null;
  technical_data: Record<string, unknown>;
  alternative_attempted: boolean;
  alternative_description: string | null;
  is_terminal: boolean;
  resolved: boolean;
  resolved_at: string | null;
  resolved_by_user_id: UUID | null;
  created_at: string;
}

export interface FailureListFilters {
  failure_type?: FailureType;
  failure_source?: FailureSource;
  resolved?: boolean;
  limit?: number;
  offset?: number;
}

export enum CapabilityGapStatus {
  OPEN = 'open',
  ACKNOWLEDGED = 'acknowledged',
  PLANNED = 'planned',
  RESOLVED = 'resolved',
  REJECTED = 'rejected',
}

export interface CapabilityGapSummaryResponse {
  id: UUID;
  request_id: UUID | null;
  department_id: UUID | null;
  requested_operation: string;
  status: CapabilityGapStatus;
  occurrence_count: number;
  first_seen_at: string;
  last_seen_at: string;
}

export interface CapabilityGapDetailResponse extends CapabilityGapSummaryResponse {
  description: string;
  safe_user_message: string;
  resolved_at: string | null;
  resolved_by_user_id: UUID | null;
  resolution_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CapabilityGapStatusUpdate {
  status: CapabilityGapStatus;
  resolution_notes?: string | null;
}

export interface CapabilityGapListFilters {
  status?: CapabilityGapStatus;
  limit?: number;
  offset?: number;
}

// ---------------------------------------------------------------------------
// RAG Knowledge Document types (Step 34)
// ---------------------------------------------------------------------------

export enum KnowledgeDocumentType {
  POLICY = 'policy',
  PROCEDURE = 'procedure',
  MANUAL = 'manual',
  FAQ = 'faq',
  PRODUCT_DOCUMENTATION = 'product_documentation',
  TROUBLESHOOTING_GUIDE = 'troubleshooting_guide',
  BENEFITS_DOCUMENT = 'benefits_document',
  INTERNAL_RULE = 'internal_rule',
  OTHER = 'other',
}

export enum KnowledgeDepartmentScope {
  SHARED = 'shared',
  CUSTOMER_SUPPORT = 'customer_support',
  HR = 'hr',
  IT = 'it',
  FINANCE = 'finance',
  PROCUREMENT = 'procurement',
}

export enum KnowledgeAccessScope {
  ALL_AUTHENTICATED = 'all_authenticated',
  EMPLOYEES = 'employees',
  DEPARTMENT_MANAGERS = 'department_managers',
  COMPANY_ACCOUNT = 'company_account',
  INTERNAL_SYSTEM = 'internal_system',
}

export enum KnowledgeDocumentStatus {
  DRAFT = 'draft',
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  SUPERSEDED = 'superseded',
  DELETED = 'deleted',
}

export enum KnowledgeIngestionStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export interface KnowledgeDocumentResponse {
  id: UUID;
  title: string;
  original_filename: string;
  document_type: KnowledgeDocumentType;
  department_scope: KnowledgeDepartmentScope[];
  access_scope: KnowledgeAccessScope;
  version: number;
  status: KnowledgeDocumentStatus;
  is_active: boolean;
  effective_date: string | null;
  supersedes_document_id: UUID | null;
  mime_type: string;
  file_size_bytes: number;
  chunk_count: number;
  ingestion_status: KnowledgeIngestionStatus;
  ingestion_error_safe: string | null;
  custom_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  ingested_at: string | null;
  deleted_at: string | null;
}

export interface KnowledgeDocumentListFilters {
  document_type?: KnowledgeDocumentType;
  status?: KnowledgeDocumentStatus;
  ingestion_status?: KnowledgeIngestionStatus;
  department?: KnowledgeDepartmentScope;
  limit?: number;
  offset?: number;
}

export interface KnowledgeSearchRequest {
  query_text: string;
  department?: KnowledgeDepartmentScope | null;
  document_types?: KnowledgeDocumentType[] | null;
  top_k?: number | null;
  effective_at?: string | null;
}

export interface KnowledgeChunkResult {
  record_id: string;
  document_id: UUID;
  title: string;
  document_type: KnowledgeDocumentType;
  department_scope: KnowledgeDepartmentScope[];
  access_scope: KnowledgeAccessScope;
  version: number;
  chunk_index: number;
  chunk_text: string;
  similarity_score: number;
  source_filename: string;
  effective_date: string | null;
}
