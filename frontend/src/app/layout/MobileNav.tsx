import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { X } from 'lucide-react';
import type { AuthenticatedUser } from '../../api/types';
import { Sidebar } from './Sidebar';
import { roleLabel } from './shell-utils';
import { duration, easing } from '../../motion/tokens';
import { useFocusTrap } from '../../hooks/useFocusTrap';

interface MobileNavProps {
  isOpen: boolean;
  onClose: () => void;
  user: AuthenticatedUser | null;
}

export function MobileNav({ isOpen, onClose, user }: MobileNavProps) {
  const drawerRef = useRef<HTMLDivElement>(null);
  const reducedMotion = useReducedMotion();
  useFocusTrap(drawerRef, isOpen, onClose);

  useEffect(() => {
    if (!isOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previous; };
  }, [isOpen]);

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-overlay md:hidden" aria-hidden={false}>
          <motion.div
            className="fixed inset-0 cursor-default bg-neutral-950/55 backdrop-blur-[1px]"
            onClick={onClose}
            aria-hidden="true"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: reducedMotion ? 0 : duration.fast }}
          />
          <motion.div
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
            tabIndex={-1}
            className="fixed inset-y-0 left-0 flex w-[min(20rem,calc(100vw-2rem))] flex-col overflow-hidden bg-white shadow-overlay dark:bg-neutral-900"
            initial={reducedMotion ? false : { x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ duration: reducedMotion ? 0 : duration.panel, ease: easing.easeOut }}
          >
            <div className="flex h-16 shrink-0 items-center justify-between border-b border-neutral-200 px-4 dark:border-neutral-800">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-neutral-950 dark:text-white">TellUS AI</p>
                <p className="truncate text-xs text-neutral-500">{user ? roleLabel(user) : 'Workspace'}</p>
              </div>
              <button
                onClick={onClose}
                className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                aria-label="Close navigation"
              >
                <X size={20} aria-hidden="true" />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto py-4">
              <Sidebar user={user} onNavigate={onClose} />
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
