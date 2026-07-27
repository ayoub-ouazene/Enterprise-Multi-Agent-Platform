import { useId, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, X } from 'lucide-react';
import { scaleIn, fadeIn } from '../../motion/tokens';
import { Button } from './Button';
import { useFocusTrap } from '../../hooks/useFocusTrap';

interface ConfirmDialogProps {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmVariant?: 'danger' | 'primary';
  isOpen: boolean;
  isPending?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  confirmVariant = 'primary',
  isOpen,
  isPending = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const messageId = useId();
  useFocusTrap(dialogRef, isOpen, onCancel);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: fadeIn.transition.duration, ease: fadeIn.transition.ease }}
          onClick={onCancel}
          role="alertdialog"
          aria-modal="true"
          aria-labelledby={titleId}
          aria-describedby={messageId}
        >
          <motion.div
            ref={dialogRef}
            tabIndex={-1}
            className="w-full max-w-sm rounded-xl bg-white p-5 shadow-xl dark:bg-neutral-800"
            initial={scaleIn.initial}
            animate={scaleIn.animate}
            exit={scaleIn.exit}
            transition={{ duration: fadeIn.transition.duration, ease: fadeIn.transition.ease }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-600 dark:bg-amber-900/30">
                <AlertTriangle size={16} aria-hidden="true" />
              </div>
              <div className="min-w-0 flex-1">
                <h3
                  id={titleId}
                  className="text-sm font-semibold text-neutral-900 dark:text-neutral-100"
                >
                  {title}
                </h3>
                <p
                  id={messageId}
                  className="mt-1 text-sm text-neutral-600 dark:text-neutral-400"
                >
                  {message}
                </p>
              </div>
              <button
                onClick={onCancel}
                className="shrink-0 rounded p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 dark:hover:bg-neutral-700 dark:hover:text-neutral-300"
                aria-label="Close"
              >
                <X size={14} />
              </button>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="secondary" onClick={onCancel} disabled={isPending}>
                {cancelLabel}
              </Button>
              <Button
                variant={confirmVariant === 'danger' ? 'danger' : 'primary'}
                onClick={onConfirm}
                isLoading={isPending}
              >
                {confirmLabel}
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
