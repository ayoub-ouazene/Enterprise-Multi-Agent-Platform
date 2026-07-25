// Motion design tokens — durations, easings, and distances
// Used by shared motion components and AnimatePresence wrappers.
// Respects prefers-reduced-motion via CSS media query.

export const duration = {
  fast: 0.15,
  normal: 0.25,
  emphasis: 0.35,
  panel: 0.3,
  page: 0.2,
} as const;

export const easing = {
  easeOut: [0, 0, 0.2, 1],
  easeInOut: [0.4, 0, 0.2, 1],
  springy: { type: "spring" as const, stiffness: 300, damping: 30 },
} as const;

export const distance = {
  subtle: 4,
  small: 8,
  medium: 16,
  large: 24,
} as const;

export const fadeInUp = {
  initial: { opacity: 0, y: distance.small },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: distance.subtle },
  transition: { duration: duration.normal, ease: easing.easeOut },
} as const;

export const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: duration.fast, ease: easing.easeOut },
} as const;

export const slideInRight = {
  initial: { x: "-100%", opacity: 0 },
  animate: { x: 0, opacity: 1 },
  exit: { x: "-100%", opacity: 0 },
  transition: { duration: duration.panel, ease: easing.easeOut },
} as const;

export const scaleIn = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.96 },
  transition: { duration: duration.normal, ease: easing.easeOut },
} as const;
