import { forwardRef, useState, type InputHTMLAttributes, type ReactNode } from 'react';
import { Eye, EyeOff, LockKeyhole, Network, ShieldCheck } from 'lucide-react';
import { clsx } from 'clsx';
import { motion, useReducedMotion } from 'framer-motion';
import { PublicHeader } from '../public/PublicHeader';
import { PublicFooter } from '../public/PublicFooter';
import { Alert, type AlertVariant } from '../ui/Alert';
import { AnimatedBackground } from '../backgrounds/AnimatedBackground';
import { NoiseTexture } from '../backgrounds/NoiseTexture';

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen bg-neutral-950 text-neutral-950 dark:bg-neutral-950 dark:text-white">
      <AnimatedBackground variant="aurora" intensity="medium" className="absolute inset-0" />
      <div className="dot-grid absolute inset-0 opacity-20" aria-hidden="true" />
      <NoiseTexture opacity={0.025} className="absolute inset-0 z-[1]" />
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <PublicHeader />
      <main id="main-content" className="relative z-10">{children}</main>
      <PublicFooter />
    </div>
  );
}

export function AuthPanel({
  children,
  illustration,
  formFirstOnMobile = true,
}: {
  children: ReactNode;
  illustration: ReactNode;
  formFirstOnMobile?: boolean;
}) {
  const reducedMotion = useReducedMotion();
  return (
    <section className="app-container py-8 sm:py-12 lg:py-16">
      <motion.div
        className="mx-auto grid max-w-6xl overflow-hidden rounded-3xl border border-neutral-200 bg-white shadow-[0_24px_80px_-32px_rgba(15,23,42,0.3)] dark:border-neutral-800 dark:bg-neutral-900 lg:grid-cols-[0.9fr_1.1fr]"
        initial={reducedMotion ? false : { opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reducedMotion ? 0 : 0.5, ease: [0.2, 0, 0, 1] }}
      >
        <div className={clsx('min-w-0 p-6 sm:p-10 lg:p-12', formFirstOnMobile ? 'order-1 lg:order-2' : 'order-2')}>{children}</div>
        <div className={clsx('min-w-0', formFirstOnMobile ? 'order-2 lg:order-1' : 'order-1')}>{illustration}</div>
      </motion.div>
    </section>
  );
}

export function AuthIllustration({ variant }: { variant: 'signup' | 'login' | 'password' }) {
  const reducedMotion = useReducedMotion();
  const content = {
    signup: {
      eyebrow: 'A workspace built around your company',
      title: 'Bring every department into one controlled request flow.',
      points: ['Five specialized departments', 'Company-scoped knowledge', 'Human approval for important actions'],
    },
    login: {
      eyebrow: 'Secure workspace entry',
      title: 'Return to requests, decisions, and live progress.',
      points: ['Workspace-aware authentication', 'Role-specific access', 'Trusted company context'],
    },
    password: {
      eyebrow: 'Protect your account',
      title: 'Replace the temporary password before entering your workspace.',
      points: ['Private password hashing', 'Session remains company-scoped', 'No temporary password is retained'],
    },
  }[variant];

  return (
    <aside className="relative flex h-full min-h-[320px] flex-col justify-between overflow-hidden bg-neutral-950/50 p-7 text-white sm:p-10 lg:min-h-[650px] lg:p-12">
      <div className="absolute inset-0 auth-grid opacity-30" aria-hidden="true" />
      <div className="absolute -right-24 top-10 h-64 w-64 rounded-full bg-primary-500/20 blur-3xl floating-glow" aria-hidden="true" />
      <div className="absolute -left-16 bottom-20 h-56 w-56 rounded-full bg-violet-600/10 blur-3xl" aria-hidden="true" />
      <div className="absolute inset-0 bg-gradient-to-br from-primary-500/5 via-transparent to-violet-500/5" aria-hidden="true" />
      <div className="relative">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary-300">{content.eyebrow}</p>
        <h2 className="mt-5 max-w-lg text-3xl font-bold leading-tight sm:text-4xl">{content.title}</h2>
        <ul className="mt-8 space-y-4">
          {content.points.map((point, i) => (
            <motion.li
              key={point}
              className="flex items-center gap-3 text-sm text-neutral-300"
              initial={reducedMotion ? false : { opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: reducedMotion ? 0 : 0.4, delay: 0.2 + i * 0.1 }}
            >
              <ShieldCheck size={18} className="shrink-0 text-primary-300" aria-hidden="true" />
              {point}
            </motion.li>
          ))}
        </ul>
      </div>
      <div className="relative mt-10 rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur">
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <span className="flex items-center gap-2 text-sm font-semibold"><Network size={16} /> Request workspace</span>
          <span className="inline-flex items-center gap-1.5 text-xs text-emerald-300"><span className="h-2 w-2 rounded-full bg-emerald-400 motion-safe:animate-pulse" /> Controlled</span>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-[11px] text-neutral-300">
          {['Routed', 'In progress', 'Review'].map((label, index) => (
            <div key={label} className="rounded-lg bg-black/20 px-2 py-3">
              <span className="mx-auto mb-2 block h-1.5 rounded-full bg-primary-400" style={{ width: `${42 + index * 18}%` }} />
              {label}
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}

export const PasswordField = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
  helperText?: string;
}>(function PasswordField({ label, error, helperText, id, name, className, ...props }, ref) {
  const [visible, setVisible] = useState(false);
  const inputId = id ?? name;
  const errorId = error ? `${inputId}-error` : undefined;
  const helperId = helperText && !error ? `${inputId}-helper` : undefined;
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{label}</label>
      <div className="relative">
        <LockKeyhole size={17} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-neutral-400" aria-hidden="true" />
        <input
          {...props}
          ref={ref}
          id={inputId}
          name={name}
          type={visible ? 'text' : 'password'}
          aria-invalid={Boolean(error)}
          aria-describedby={[errorId, helperId].filter(Boolean).join(' ') || undefined}
          className={clsx(
            'h-12 w-full rounded-xl border bg-white pl-10 pr-12 text-base text-neutral-950 shadow-xs transition focus:border-primary-500 dark:bg-neutral-950 dark:text-white',
            error ? 'border-danger-500' : 'border-neutral-300 dark:border-neutral-700',
            className,
          )}
        />
        <button
          type="button"
          onClick={() => setVisible((value) => !value)}
          className="absolute right-1.5 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-lg text-neutral-500 hover:bg-neutral-100 hover:text-neutral-800 dark:hover:bg-neutral-800 dark:hover:text-white"
          aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          aria-pressed={visible}
        >
          {visible ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
        </button>
      </div>
      {error && <p id={errorId} role="alert" className="text-sm text-danger-600 dark:text-danger-400">{error}</p>}
      {helperText && !error && <p id={helperId} className="text-sm leading-5 text-neutral-500 dark:text-neutral-400">{helperText}</p>}
    </div>
  );
});

export function FormErrorSummary({ errors }: { errors: string[] }) {
  if (!errors.length) return null;
  return (
    <div className="rounded-xl border border-danger-200 bg-danger-50 p-4 text-danger-900 dark:border-danger-900 dark:bg-danger-950 dark:text-danger-100" role="alert" aria-live="polite">
      <p className="font-semibold">Review the following:</p>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
        {errors.map((error) => <li key={error}>{error}</li>)}
      </ul>
    </div>
  );
}

export function AuthStatusMessage({ variant, title, children }: { variant: AlertVariant; title: string; children: ReactNode }) {
  return <Alert variant={variant} title={title} aria-live={variant === 'error' ? 'assertive' : 'polite'}>{children}</Alert>;
}
