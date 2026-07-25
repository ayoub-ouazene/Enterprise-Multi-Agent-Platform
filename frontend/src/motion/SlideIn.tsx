import { motion } from 'framer-motion';
import type { ReactNode } from 'react';

interface SlideInProps {
  children: ReactNode;
  className?: string;
  direction?: 'left' | 'right';
}

export function SlideIn({ children, className, direction = 'left' }: SlideInProps) {
  const x = direction === 'left' ? '-100%' : '100%';
  return (
    <motion.div
      className={className}
      initial={{ x, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x, opacity: 0 }}
      transition={{ duration: 0.3, ease: [0, 0, 0.2, 1] }}
    >
      {children}
    </motion.div>
  );
}
