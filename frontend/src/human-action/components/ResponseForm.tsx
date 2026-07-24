import { useState, useMemo } from 'react';
import { AlertTriangle, CheckCircle } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Alert } from '../../components/ui/Alert';
import { getActionTypeConfig } from '../registry';
import type { HumanActionDetail } from '../../api/types';

interface ResponseFormProps {
  action: HumanActionDetail;
  onSubmit: (decision: string, responseFields: Record<string, unknown>) => void;
  isSubmitting: boolean;
}

export function ResponseForm({ action, onSubmit, isSubmitting }: ResponseFormProps) {
  const [decision, setDecision] = useState<string>('');
  const [notes, setNotes] = useState('');
  const [selectedOption, setSelectedOption] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const config = useMemo(() => getActionTypeConfig(action.action_type), [action.action_type]);

  const options = action.decision_package?.options as Array<{id: string; label: string}> | undefined;
  const hasOptions = Array.isArray(options) && options.length > 0;

  const requiresReason = ['rejected', 'failed', 'unable'].some(r => decision.toLowerCase().includes(r));

  const canSubmit = decision.trim() !== '' && (!requiresReason || notes.trim().length > 0) && !isSubmitting;

  const handleSubmit = () => {
    if (!decision.trim()) {
      setError('Please select a decision.');
      return;
    }
    if (requiresReason && !notes.trim()) {
      setError(`A reason or notes are required when selecting "${decision}".`);
      return;
    }

    const fields: Record<string, unknown> = { notes: notes.trim() };
    if (hasOptions && selectedOption) {
      fields.selected_option = selectedOption;
    }

    setError(null);
    onSubmit(decision, fields);
  };

  const isNotPending = action.status !== 'pending';

  if (isNotPending) {
    return (
      <Alert variant="info" title="Action completed">
        This action has already been {action.status}.
      </Alert>
    );
  }

  if (!action.can_respond) {
    return (
      <Alert variant="warning" title="Cannot respond">
        You are not authorized to respond to this action, or the action window has expired.
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
        Your Response
      </h3>

      {/* Decision selection */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
          Decision
        </label>
        <div className="flex flex-wrap gap-2">
          {action.allowed_decisions.map((d) => {
            const active = decision === d;
            const isPositive = ['approved', 'completed', 'selected', 'verified', 'submitted'].some(
              p => d.toLowerCase() === p
            );
            return (
              <button
                key={d}
                type="button"
                onClick={() => {
                  setDecision(d);
                  setError(null);
                }}
                className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 ${
                  active
                    ? isPositive
                      ? 'border-success-500 bg-success-50 text-success-700 dark:border-success-500 dark:bg-success-900 dark:text-success-200'
                      : 'border-danger-500 bg-danger-50 text-danger-700 dark:border-danger-500 dark:bg-danger-900 dark:text-danger-200'
                    : 'border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:bg-neutral-700'
                }`}
                aria-pressed={active}
              >
                {active && (isPositive ? <CheckCircle size={14} /> : <AlertTriangle size={14} />)}
                {capitalize(d)}
              </button>
            );
          })}
        </div>
      </div>

      {/* Options from decision_package */}
      {hasOptions && (
        <div className="space-y-2">
          <label className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            {config.label} Options
          </label>
          <div className="space-y-2">
            {options.map((opt) => (
              <label
                key={opt.id}
                className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors ${
                  selectedOption === opt.id
                    ? 'border-primary-500 bg-primary-50 dark:border-primary-500 dark:bg-primary-900'
                    : 'border-neutral-200 bg-white hover:bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-800 dark:hover:bg-neutral-750'
                }`}
              >
                <input
                  type="radio"
                  name="option"
                  value={opt.id}
                  checked={selectedOption === opt.id}
                  onChange={() => setSelectedOption(opt.id)}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-neutral-900 dark:text-neutral-100">{opt.label}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Notes / Reason */}
      <div className="space-y-2">
        <label htmlFor="action-notes" className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
          {requiresReason ? 'Reason / Explanation *' : 'Notes (optional)'}
        </label>
        <textarea
          id="action-notes"
          rows={4}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder={requiresReason ? 'Explain your decision...' : 'Add any relevant notes...'}
          className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 placeholder-neutral-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100"
        />
      </div>

      {error && (
        <Alert variant="error" title="Validation error">
          {error}
        </Alert>
      )}

      <div className="flex items-center gap-2 pt-2">
        <Button onClick={handleSubmit} isLoading={isSubmitting} disabled={!canSubmit}>
          Submit Response
        </Button>
        {isSubmitting && (
          <span className="text-sm text-neutral-500 dark:text-neutral-400">Submitting...</span>
        )}
      </div>
    </div>
  );
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ');
}
