import { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { fadeIn, scaleIn } from '../../motion/tokens';

interface ModalProps {
  title: string;
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

export function Modal({ title, isOpen, onClose, children }: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    if (isOpen) {
      document.addEventListener('keydown', onKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          ref={overlayRef}
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 p-4 pt-20"
          onClick={(e) => {
            if (e.target === overlayRef.current) onClose();
          }}
          role="dialog"
          aria-modal="true"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: fadeIn.transition.duration, ease: fadeIn.transition.ease }}
        >
          <motion.div
            className="w-full max-w-lg rounded-lg border border-neutral-200 bg-white shadow-xl dark:border-neutral-700 dark:bg-neutral-900"
            initial={scaleIn.initial}
            animate={scaleIn.animate}
            exit={scaleIn.exit}
            transition={{ duration: fadeIn.transition.duration, ease: fadeIn.transition.ease }}
          >
            <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3 dark:border-neutral-700">
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{title}</h3>
              <button
                onClick={onClose}
                className="rounded p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 dark:hover:bg-neutral-800 dark:hover:text-neutral-300"
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>
            <div className="px-4 py-4">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
