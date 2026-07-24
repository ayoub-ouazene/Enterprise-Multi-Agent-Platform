import { CheckCircle, User } from 'lucide-react';
import { formatDateTime } from '../../lib/formatters';
import type { HumanActionDetail } from '../../api/types';

interface ActionHistoryProps {
  action: HumanActionDetail;
}

export function ActionHistory({ action }: ActionHistoryProps) {
  if (!action.response || Object.keys(action.response).length === 0) {
    return (
      <p className="text-sm italic text-neutral-500 dark:text-neutral-400">
        No response recorded yet.
      </p>
    );
  }

  const resp = action.response;
  const decision = (resp.decision as string | undefined) ?? '—';
  const respondedAt = resp.responded_at as string | undefined;
  const respondingUserId = resp.responding_user_id as string | undefined;
  const responseText = (resp.response as string | undefined) ?? '';

  let parsed: Record<string, unknown> | null = null;
  try {
    parsed = JSON.parse(responseText) as Record<string, unknown>;
  } catch {
    parsed = null;
  }

  const notesText = parsed && parsed.notes !== undefined ? String(parsed.notes) : '';
  const selectedText = parsed && parsed.selected_option !== undefined ? String(parsed.selected_option) : '';

  return (
    <div className="space-y-3">
      <div
        className={`flex items-start gap-3 rounded-lg border p-4 ${
          action.status === 'resolved'
            ? 'border-success-200 bg-success-50 dark:border-success-800 dark:bg-success-900/30'
            : 'border-neutral-200 bg-white dark:border-neutral-700 dark:bg-neutral-800'
        }`}
      >
        <div className="mt-0.5 shrink-0">
          <CheckCircle
            size={18}
            className="text-success-600 dark:text-success-400"
            aria-hidden="true"
          />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold capitalize text-neutral-900 dark:text-neutral-100">
              {decision}
            </span>
            {action.status === 'resolved' && (
              <span className="inline-flex items-center rounded-full bg-success-100 px-2 py-0.5 text-[10px] font-bold uppercase text-success-700 dark:bg-success-900 dark:text-success-300">
                Resolved
              </span>
            )}
          </div>

          {notesText && (
            <p className="mt-1 text-sm text-neutral-700 dark:text-neutral-300">
              {notesText}
            </p>
          )}

          {selectedText && (
            <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
              <span className="font-medium">Selected:</span>{' '}
              {selectedText}
            </p>
          )}

          {!parsed && responseText && (
            <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">{responseText}</p>
          )}

          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400">
            {respondingUserId && (
              <span className="inline-flex items-center gap-1">
                <User size={12} aria-hidden="true" />
                {respondingUserId.slice(0, 8)}...
              </span>
            )}
            {respondedAt && (
              <span>{formatDateTime(respondedAt)}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
