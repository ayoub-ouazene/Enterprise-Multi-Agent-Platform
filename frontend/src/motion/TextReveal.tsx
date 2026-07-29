import { motion, useReducedMotion, type Variants } from 'framer-motion';

interface TextRevealProps {
  text: string;
  className?: string;
  delay?: number;
  stagger?: number;
  as?: 'h1' | 'h2' | 'h3' | 'p' | 'span';
}

/**
 * Word-by-word text reveal — splits text into words and staggers their entrance.
 * Inspired by reactbits.dev text animations.
 * Respects prefers-reduced-motion (renders plain text).
 */
export function TextReveal({
  text,
  className,
  delay = 0,
  stagger = 0.06,
  as = 'h2',
}: TextRevealProps) {
  const reducedMotion = useReducedMotion();
  const MotionTag = motion[as];

  if (reducedMotion) {
    const Tag = as;
    return <Tag className={className}>{text}</Tag>;
  }

  const words = text.split(' ');
  const container: Variants = {
    hidden: {},
    show: { transition: { staggerChildren: stagger, delayChildren: delay } },
  };
  const word: Variants = {
    hidden: { opacity: 0, y: '0.6em', filter: 'blur(6px)' },
    show: {
      opacity: 1,
      y: 0,
      filter: 'blur(0px)',
      transition: { duration: 0.5, ease: [0.2, 0, 0, 1] },
    },
  };

  return (
    <MotionTag
      className={className}
      variants={container}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, amount: 0.4 }}
      aria-label={text}
    >
      {words.map((w, i) => (
        <span key={`${w}-${i}`} className="inline-block overflow-hidden align-bottom">
          <motion.span variants={word} className="inline-block">
            {w}
            {i < words.length - 1 ? '\u00A0' : ''}
          </motion.span>
        </span>
      ))}
    </MotionTag>
  );
}

interface AnimatedCounterProps {
  value: number;
  duration?: number;
  className?: string;
  suffix?: string;
  prefix?: string;
}

/**
 * Animated number counter — counts up when scrolled into view.
 */
export function AnimatedCounter({
  value,
  duration = 1.4,
  className,
  suffix = '',
  prefix = '',
}: AnimatedCounterProps) {
  const reducedMotion = useReducedMotion();

  if (reducedMotion) {
    return <span className={className}>{prefix}{value}{suffix}</span>;
  }

  return (
    <motion.span
      className={className}
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
    >
      <CountUp end={value} duration={duration} prefix={prefix} suffix={suffix} />
    </motion.span>
  );
}

import { useEffect, useState } from 'react';

function CountUp({ end, duration, prefix, suffix }: { end: number; duration: number; prefix: string; suffix: string }) {
  const [count, setCount] = useState(0);
  const [ref, setRef] = useState<HTMLSpanElement | null>(null);

  useEffect(() => {
    if (!ref) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          const start = performance.now();
          const tick = (now: number) => {
            const progress = Math.min((now - start) / (duration * 1000), 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setCount(Math.round(end * eased));
            if (progress < 1) requestAnimationFrame(tick);
          };
          requestAnimationFrame(tick);
          observer.disconnect();
        }
      },
      { threshold: 0.4 }
    );
    observer.observe(ref);
    return () => observer.disconnect();
  }, [ref, end, duration]);

  return <span ref={setRef}>{prefix}{count}{suffix}</span>;
}
