/**
 * Authoritative status system mapping all backend statuses to UI semantics.
 */
export type StatusCategory =
  | 'neutral'
  | 'info'
  | 'inProgress'
  | 'pending'
  | 'attention'
  | 'success'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface StatusMeta {
  label: string;
  category: StatusCategory;
  description: string;
  terminal: boolean;
  attention: boolean;
}

const requestStatusMap: Record<string, StatusMeta> = {
  created:                    { label: 'Submitted', category: 'neutral', description: 'Received and ready for routing.', terminal: false, attention: false },
  routing:                    { label: 'Being routed', category: 'info', description: 'Selecting the appropriate owner department.', terminal: false, attention: false },
  processing:                 { label: 'In progress', category: 'inProgress', description: 'The owner department is working on this request.', terminal: false, attention: false },
  waiting_for_department:     { label: 'Another department is assisting', category: 'pending', description: 'An authorized department is contributing.', terminal: false, attention: false },
  waiting_for_human_approval: { label: 'Waiting for approval', category: 'pending', description: 'An authorized decision is required.', terminal: false, attention: true },
  waiting_for_human_action:   { label: 'Waiting for information or manual work', category: 'attention', description: 'A person must complete an assigned action.', terminal: false, attention: true },
  under_review:               { label: 'Quality check', category: 'inProgress', description: 'An internal quality check is in progress.', terminal: false, attention: false },
  completed:                  { label: 'Completed', category: 'success', description: 'The request completed successfully.', terminal: true, attention: false },
  rejected:                   { label: 'Rejected', category: 'failed', description: 'The request was not approved.', terminal: true, attention: true },
  cancelled:                  { label: 'Cancelled', category: 'cancelled', description: 'The request will not continue.', terminal: true, attention: false },
  failed:                     { label: 'Failed', category: 'failed', description: 'The request could not be completed.', terminal: true, attention: true },
};

type BasicStatusMeta = Pick<StatusMeta, 'label' | 'category'>;

const humanActionStatusMap: Record<string, BasicStatusMeta> = {
  pending:   { label: 'Pending',   category: 'pending' },
  resolved:  { label: 'Resolved',  category: 'success' },
  cancelled: { label: 'Cancelled', category: 'cancelled' },
  overdue:   { label: 'Overdue',   category: 'attention' },
};

const importJobStatusMap: Record<string, BasicStatusMeta> = {
  queued:     { label: 'Queued',     category: 'neutral' },
  processing: { label: 'Processing', category: 'inProgress' },
  completed:  { label: 'Completed',  category: 'success' },
  failed:     { label: 'Failed',     category: 'failed' },
};

const notificationSeverityMap: Record<string, BasicStatusMeta> = {
  info:    { label: 'Info',    category: 'neutral' },
  success: { label: 'Success', category: 'success' },
  warning: { label: 'Warning', category: 'attention' },
  error:   { label: 'Error',   category: 'failed' },
};

export function getRequestStatusMeta(status: string): StatusMeta {
  return requestStatusMap[status] ?? { label: 'Status unavailable', category: 'neutral', description: 'The latest state is unavailable.', terminal: false, attention: false };
}

export function getHumanActionStatusMeta(status: string): StatusMeta {
  const meta = humanActionStatusMap[status] ?? { label: status, category: 'neutral' };
  return { ...meta, description: '', terminal: status !== 'pending', attention: status === 'pending' };
}

export function getImportJobStatusMeta(status: string): StatusMeta {
  const meta = importJobStatusMap[status] ?? { label: status, category: 'neutral' };
  return { ...meta, description: '', terminal: status === 'completed' || status === 'failed', attention: status === 'failed' };
}

export function getNotificationSeverityMeta(severity: string): StatusMeta {
  const meta = notificationSeverityMap[severity] ?? { label: severity, category: 'neutral' };
  return { ...meta, description: '', terminal: true, attention: severity === 'warning' || severity === 'error' };
}

/**
 * Maps a status category to Tailwind color tokens used in Badge/StatusDot.
 */
export const statusCategoryStyles: Record<StatusCategory, { badgeClass: string; dotClass: string }> = {
  neutral:   { badgeClass: 'bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200', dotClass: 'bg-neutral-400' },
  info:      { badgeClass: 'bg-info-100 text-info-800 dark:bg-info-900 dark:text-info-200', dotClass: 'bg-info-500' },
  inProgress:{ badgeClass: 'bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200', dotClass: 'bg-primary-500' },
  pending:   { badgeClass: 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-200', dotClass: 'bg-warning-500' },
  attention: { badgeClass: 'bg-danger-100 text-danger-800 dark:bg-danger-900 dark:text-danger-200', dotClass: 'bg-danger-500' },
  success:   { badgeClass: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-200', dotClass: 'bg-success-500' },
  completed: { badgeClass: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-200', dotClass: 'bg-success-500' },
  failed:    { badgeClass: 'bg-danger-100 text-danger-800 dark:bg-danger-900 dark:text-danger-200', dotClass: 'bg-danger-500' },
  cancelled: { badgeClass: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300', dotClass: 'bg-neutral-400' },
};

export const statusAccentColors: Record<StatusCategory, string> = {
  neutral:   'bg-neutral-400',
  info:      'bg-info-500',
  inProgress:'bg-primary-500',
  pending:   'bg-warning-500',
  attention: 'bg-danger-500',
  success:   'bg-success-500',
  completed: 'bg-success-500',
  failed:    'bg-danger-500',
  cancelled: 'bg-neutral-400',
};
