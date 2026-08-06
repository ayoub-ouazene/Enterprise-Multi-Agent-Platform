import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { X } from 'lucide-react';
import type { AuthenticatedUser } from '../../api/types';
import { Sidebar } from './Sidebar';
import { BrandMark } from '../../components/public/BrandMark';
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
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 cursor-default bg-slate-950/70 backdrop-blur-sm"
            onClick={onClose}
            aria-hidden="true"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: reducedMotion ? 0 : duration.fast }}
          />

          {/* Drawer */}
          <motion.div
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
            tabIndex={-1}
            className="fixed inset-y-0 left-0 flex w-[min(20rem,calc(100vw-2rem))] flex-col overflow-hidden border-r border-white/10 bg-slate-900 shadow-2xl dark:bg-slate-950"
            initial={reducedMotion ? false : { x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ duration: reducedMotion ? 0 : duration.panel, ease: easing.easeOut }}
          >
            {/* Drawer header */}
            <div className="flex h-[3.75rem] shrink-0 items-center justify-between border-b border-white/10 px-4">
              <div className="flex items-center gap-3">
                <BrandMark tabIndex={-1} />
              </div>
              <button
                onClick={onClose}
                className="inline-flex h-10 w-10 items-center justify-center rounded-xl text-white/70 transition hover:bg-white/10 hover:text-white"
                aria-label="Close navigation"
                autoFocus
              >
                <X size={20} />
              </button>
            </div>

            {/* Nav content */}
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
