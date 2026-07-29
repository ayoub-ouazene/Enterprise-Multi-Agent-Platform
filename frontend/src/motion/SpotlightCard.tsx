import { motion, useReducedMotion, type Variants } from 'framer-motion';
import type { ReactNode } from 'react';

interface SpotlightCardProps {
  children: ReactNode;
  className?: string;
  spotlightColor?: string;
  /** Disable the hover spotlight (e.g. for reduced motion) */
  disabled?: boolean;
}

/**
 * Card with a cursor-following radial spotlight glow on hover.
 * Inspired by reactbits.dev spotlight cards.
 */
export function SpotlightCard({
  children,
  className,
  spotlightColor = 'rgba(99, 102, 241, 0.18)',
  disabled,
}: SpotlightCardProps) {
  const reducedMotion = useReducedMotion();
  const isDisabled = disabled ?? Boolean(reducedMotion);

  return (
    <motion.div
      className={`group/spotlight relative overflow-hidden ${className ?? ''}`}
      whileHover={isDisabled ? undefined : { y: -4 }}
      transition={{ type: 'spring', stiffness: 300, damping: 22 }}
    >
      <motion.div
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover/spotlight:opacity-100"
        style={{
          background: `radial-gradient(280px circle at var(--mx, 50%) var(--my, 50%), ${spotlightColor}, transparent 70%)`,
        }}
        aria-hidden="true"
      />
      {children}
    </motion.div>
  );
}

interface StaggerListProps {
  children: ReactNode;
  className?: string;
  stagger?: number;
  amount?: number;
}

const itemV: Variants = {
  hidden: { opacity: 0, y: 14, filter: 'blur(4px)' },
  show: { opacity: 1, y: 0, filter: 'blur(0px)', transition: { duration: 0.45, ease: [0.2, 0, 0, 1] } },
};

const containerV: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07 } },
};

export function StaggerList({ children, className, stagger = 0.07 }: StaggerListProps) {
  const reducedMotion = useReducedMotion();
  if (reducedMotion) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      variants={{ ...containerV, show: { transition: { staggerChildren: stagger } } }}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, amount: 0.2 }}
    >
      {children}
    </motion.div>
  );
}

export function StaggerListItem({ children, className }: { children: ReactNode; className?: string }) {
  const reducedMotion = useReducedMotion();
  if (reducedMotion) return <div className={className}>{children}</div>;
  return <motion.div className={className} variants={itemV}>{children}</motion.div>;
}
