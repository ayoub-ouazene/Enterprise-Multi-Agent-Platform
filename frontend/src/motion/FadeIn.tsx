import { motion } from 'framer-motion';
import { fadeIn } from './tokens';
import type { ReactNode } from 'react';

interface FadeInProps {
  children: ReactNode;
  className?: string;
  delay?: number;
}

export function FadeIn({ children, className, delay = 0 }: FadeInProps) {
  return (
    <motion.div
      className={className}
      initial={fadeIn.initial}
      animate={fadeIn.animate}
      exit={fadeIn.exit}
      transition={{ ...fadeIn.transition, delay }}
    >
      {children}
    </motion.div>
  );
}
