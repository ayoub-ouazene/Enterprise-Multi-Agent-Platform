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
  description?: string;
}

const requestStatusMap: Record<string, StatusMeta> = {
  created:                    { label: 'Created',                       category: 'neutral' },
  routing:                    { label: 'Routing',                       category: 'info' },
  processing:                 { label: 'Processing',                    category: 'inProgress' },
  waiting_for_department:     { label: 'Waiting for Department',       category: 'pending' },
  waiting_for_human_approval: { label: 'Waiting for Approval',         category: 'pending' },
  waiting_for_human_action:   { label: 'Waiting for Action',           category: 'attention' },
  under_review:               { label: 'Under Review',                 category: 'inProgress' },
  completed:                  { label: 'Completed',                     category: 'success' },
  rejected:                   { label: 'Rejected',                      category: 'failed' },
  cancelled:                  { label: 'Cancelled',                     category: 'cancelled' },
  failed:                     { label: 'Failed',                        category: 'failed' },
};

const humanActionStatusMap: Record<string, StatusMeta> = {
  pending:   { label: 'Pending',   category: 'pending' },
  resolved:  { label: 'Resolved',  category: 'success' },
  cancelled: { label: 'Cancelled', category: 'cancelled' },
  overdue:   { label: 'Overdue',   category: 'attention' },
};

const importJobStatusMap: Record<string, StatusMeta> = {
  queued:     { label: 'Queued',     category: 'neutral' },
  processing: { label: 'Processing', category: 'inProgress' },
  completed:  { label: 'Completed',  category: 'success' },
  failed:     { label: 'Failed',     category: 'failed' },
};

const notificationSeverityMap: Record<string, StatusMeta> = {
  info:    { label: 'Info',    category: 'neutral' },
  success: { label: 'Success', category: 'success' },
  warning: { label: 'Warning', category: 'attention' },
  error:   { label: 'Error',   category: 'failed' },
};

export function getRequestStatusMeta(status: string): StatusMeta {
  return requestStatusMap[status] ?? { label: status, category: 'neutral' };
}

export function getHumanActionStatusMeta(status: string): StatusMeta {
  return humanActionStatusMap[status] ?? { label: status, category: 'neutral' };
}

export function getImportJobStatusMeta(status: string): StatusMeta {
  return importJobStatusMap[status] ?? { label: status, category: 'neutral' };
}

export function getNotificationSeverityMeta(severity: string): StatusMeta {
  return notificationSeverityMap[severity] ?? { label: severity, category: 'neutral' };
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
