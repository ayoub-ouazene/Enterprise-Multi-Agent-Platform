import { useState } from 'react';
import { Rocket, ShieldAlert, X } from 'lucide-react';
import { Button } from '../../components/ui/Button';

interface ActivationModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isActivating: boolean;
}

export function ActivationModal({ open, onClose, onConfirm, isActivating }: ActivationModalProps) {
  const [confirmText, setConfirmText] = useState('');
  const confirmed = confirmText.trim().toLowerCase() === 'activate';

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl dark:bg-neutral-800">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
            <Rocket size={20} className="text-primary-500" />
            Activate Company
          </h2>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 dark:hover:bg-neutral-700 dark:hover:text-neutral-200"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mt-4 space-y-3">
          <div className="flex items-start gap-3 rounded-lg bg-warning-50 p-3 text-sm text-warning-800 dark:bg-warning-900/30 dark:text-warning-200">
            <ShieldAlert size={18} className="mt-0.5 shrink-0" />
            <p>
              Activating your company enables all departments and makes the platform available to employees.
              This action cannot be undone.
            </p>
          </div>

          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Type <strong>activate</strong> to confirm:
          </p>
          <input
            type="text"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-neutral-600 dark:bg-neutral-700 dark:text-neutral-100"
            placeholder="activate"
            autoFocus
          />
        </div>

        <div className="mt-6 flex items-center justify-end gap-3">
          <Button variant="ghost" onClick={onClose} disabled={isActivating}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={onConfirm}
            disabled={!confirmed || isActivating}
            isLoading={isActivating}
          >
            Activate Company
          </Button>
        </div>
      </div>
    </div>
  );
}
