import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import type { AuthenticatedUser } from '../../api/types';
import { Sidebar } from './Sidebar';
import { fadeIn } from '../../motion/tokens';

interface MobileNavProps {
  isOpen: boolean;
  onClose: () => void;
  user: AuthenticatedUser | null;
}

export function MobileNav({ isOpen, onClose, user }: MobileNavProps) {
  useEffect(() => {
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/50"
            onClick={onClose}
            aria-hidden="true"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: fadeIn.transition.duration, ease: fadeIn.transition.ease }}
          />

          {/* Drawer */}
          <motion.div
            className="fixed inset-y-0 left-0 w-64 bg-white shadow-xl dark:bg-neutral-900"
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ duration: 0.3, ease: [0, 0, 0.2, 1] }}
          >
            <div className="flex h-16 items-center justify-between border-b border-neutral-200 px-4 dark:border-neutral-800">
              <span className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Menu</span>
              <button
                onClick={onClose}
                className="rounded-md p-2 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-neutral-200"
                aria-label="Close navigation"
              >
                <X size={20} aria-hidden="true" />
              </button>
            </div>
            <div className="py-4">
              <Sidebar user={user} onNavigate={onClose} />
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body
  );
}
