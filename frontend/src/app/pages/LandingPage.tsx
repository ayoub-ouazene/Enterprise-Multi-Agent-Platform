import { motion, useReducedMotion } from 'framer-motion';
import {
  ArrowRight,
  BadgeCheck,
  Banknote,
  Building2,
  CheckCircle2,
  ClipboardCheck,
  FileSearch,
  Headphones,
  HeartHandshake,
  Laptop,
  LockKeyhole,
  Radio,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Users,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { PublicHeader } from '../../components/public/PublicHeader';
import { PublicFooter } from '../../components/public/PublicFooter';
import { DemoVideoSection } from '../../components/public/DemoVideoSection';
import { accessibleMotionDuration } from '../../motion/accessibility';
import { TextReveal } from '../../motion/TextReveal';

const workflow = [
  ['Submit', 'Describe the outcome you need'],
  ['Route', 'The right department takes ownership'],
  ['Process', 'Work follows company policy'],
  ['Collaborate', 'Other departments contribute safely'],
  ['Approve', 'People decide when authority is required'],
  ['Verify', 'Important results receive a quality check'],
  ['Deliver', 'A clear result and history are returned'],
];

const departments = [
  { title: 'Customer Support', icon: Headphones, text: 'Resolve company-specific questions with grounded guidance and technical escalation.' },
  { title: 'Human Resources', icon: Users, text: 'Coordinate leave, onboarding, benefits guidance, and job-description preparation.' },
  { title: 'Information Technology', icon: Laptop, text: 'Diagnose incidents, validate inventory, and prepare controlled access operations.' },
  { title: 'Finance', icon: Banknote, text: 'Validate budgets and purchases with deterministic balances and approval controls.' },
  { title: 'Procurement', icon: ShoppingCart, text: 'Evaluate eligible suppliers using transparent scores and structured shortlists.' },
];

const controls = [
  [Building2, 'Company isolation', 'Every request, document, and decision stays scoped to its authenticated workspace.'],
  [FileSearch, 'Policy grounding', 'Company knowledge informs answers and recommendations where evidence is required.'],
  [LockKeyhole, 'Role-based access', 'Company accounts, managers, employees, and external requesters see appropriate capabilities.'],
  [HeartHandshake, 'Human control', 'Approvals appear only when judgment or authority is genuinely necessary.'],
  [ClipboardCheck, 'Auditability', 'Meaningful workflow events preserve a clear operational history.'],
  [Radio, 'Live progress', 'Request updates stay visible without interrupting normal application use.'],
];

export function LandingPage() {
  const reducedMotion = useReducedMotion();
  const reveal = {
    initial: reducedMotion ? { opacity: 1 } : { opacity: 0, y: 18 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, amount: 0.2 },
    transition: { duration: accessibleMotionDuration(reducedMotion, 0.55) },
  };

  return (
    <div className="min-h-screen overflow-x-clip bg-white text-neutral-950 dark:bg-neutral-950 dark:text-white">
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <PublicHeader transparent />
      <main id="main-content">
        {/* HERO: Enhanced with aurora + particle field */}
        <section className="relative overflow-hidden bg-neutral-950 pb-24 pt-16 text-white sm:pt-24 lg:pb-32 lg:pt-28">
          <div className="absolute inset-0" aria-hidden="true">
            <div className="absolute inset-0" style={{
              background: 'conic-gradient(from 0deg, #6366f1, #3b82f6, #8b5cf6, #6366f1)',
              opacity: 0.12,
              filter: 'blur(100px)',
              animation: 'aurora-1 8s ease-in-out infinite'
            }} />
            <div className="absolute bottom-0 right-0 h-full w-full" style={{
              background: 'conic-gradient(from 180deg, #3b82f6, #06b6d4, #6366f1, #3b82f6)',
              opacity: 0.1,
              filter: 'blur(100px)',
              animation: 'aurora-2 12s ease-in-out infinite'
            }} />
            <div className="absolute inset-0 spotlight-grid opacity-50" />
            <div className="absolute left-1/2 top-0 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-primary-600/15 blur-3xl floating-glow" />
            <div className="absolute right-10 top-32 h-72 w-72 rounded-full bg-violet-600/10 blur-3xl" />
            <div className="absolute bottom-0 left-1/4 h-96 w-96 rounded-full bg-cyan-500/5 blur-3xl" />
          </div>
          <div className="app-container relative z-10 grid items-center gap-14 lg:grid-cols-[1.05fr_0.95fr]">
            <motion.div
              initial={reducedMotion ? false : { opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: reducedMotion ? 0 : 0.6 }}
            >
              <motion.div
                className="inline-flex items-center gap-2 rounded-full border border-primary-400/20 bg-primary-400/10 px-3 py-1.5 text-sm font-semibold text-primary-200"
                initial={reducedMotion ? false : { opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: reducedMotion ? 0 : 0.5, delay: 0.1 }}
              >
                <Sparkles size={15} aria-hidden="true" /> Enterprise operations, coordinated
              </motion.div>
              <TextReveal
                as="h1"
                text="Move enterprise requests from question to controlled outcome."
                className="mt-7 max-w-4xl text-4xl font-bold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl"
                stagger={0.04}
              />
              <motion.p
                className="mt-6 max-w-2xl text-lg leading-8 text-neutral-300"
                initial={reducedMotion ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: reducedMotion ? 0 : 0.55, delay: 0.4 }}
              >
                Orchestra coordinates five specialized departments, company knowledge, live workflow progress, and human authority in one secure workspace.
              </motion.p>
              <motion.div
                className="mt-9 flex flex-col gap-3 min-[420px]:flex-row"
                initial={reducedMotion ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: reducedMotion ? 0 : 0.55, delay: 0.55 }}
              >
                <Link to="/signup" className="group inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-primary-600 px-6 py-3 font-semibold text-white shadow-lg shadow-primary-900/30 transition-[background-color,box-shadow,transform] duration-ui ease-productive hover:bg-primary-500 hover:shadow-primary-500/30 motion-safe:active:scale-[0.98]">
                  Create company workspace
                  <ArrowRight size={18} aria-hidden="true" className="transition-transform duration-ui group-hover:translate-x-0.5" />
                </Link>
                <Link to="/login" className="text-neutral-700">
                  Sign in
                </Link>
              </motion.div>
              <p className="mt-5 max-w-xl text-sm leading-6 text-neutral-400">
                Company accounts register publicly. Employees and managers are provisioned by their Company. External requesters use their approved Company-provided account.
              </p>
            </motion.div>
            <ProductPreview reducedMotion={Boolean(reducedMotion)} />
          </div>
        </section>

        <DemoVideoSection />

        <section id="product" className="scroll-mt-20 py-20 sm:py-24">
          <motion.div className="app-container" {...reveal}>
            <SectionHeading eyebrow="One operating flow" title="Complex coordination, made understandable" description="One request keeps one owner while the platform coordinates research, collaboration, approval, review, and delivery." />
            <div id="workflow" className="mt-12 overflow-x-auto pb-3" aria-label="Request workflow">
              <ol className="grid min-w-[960px] grid-cols-7 gap-0 lg:min-w-0">
                {workflow.map(([title, text], index) => (
                  <li key={title} className="group relative px-2 text-center">
                    {index < workflow.length - 1 && (
                      <span className="absolute left-1/2 top-5 h-px w-full overflow-hidden bg-neutral-200 dark:bg-neutral-700" aria-hidden="true">
                        <motion.span
                          className="block h-full origin-left bg-primary-500"
                          initial={reducedMotion ? { scaleX: 1 } : { scaleX: 0 }}
                          whileInView={{ scaleX: 1 }}
                          viewport={{ once: true }}
                          transition={{ duration: reducedMotion ? 0 : 0.5, delay: index * 0.08 }}
                        />
                      </span>
                    )}
                    <span className="relative z-10 mx-auto flex h-10 w-10 items-center justify-center rounded-full border-4 border-white bg-primary-600 text-sm font-bold text-white shadow-sm dark:border-neutral-950">
                      {index + 1}
                    </span>
                    <h3 className="mt-4 text-sm font-bold">{title}</h3>
                    <p className="mt-2 text-xs leading-5 text-neutral-500 dark:text-neutral-400">{text}</p>
                  </li>
                ))}
              </ol>
            </div>
          </motion.div>
        </section>

        <section id="departments" className="scroll-mt-20 border-y border-neutral-200 bg-neutral-50 py-20 dark:border-neutral-800 dark:bg-neutral-900/60 sm:py-24">
          <div className="app-container">
            <motion.div {...reveal}>
              <SectionHeading eyebrow="Five specialized departments" title="Deep capabilities, one Company experience" description="Each department has clear boundaries and works within the same request lifecycle." />
            </motion.div>
            <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-5">
              {departments.map((department, index) => {
                const Icon = department.icon;
                return (
                  <motion.article
                    key={department.title}
                    className="group relative overflow-hidden rounded-2xl border border-neutral-200 bg-white p-5 shadow-xs transition-[border-color,box-shadow,transform] duration-ui ease-productive hover:-translate-y-1 hover:border-primary-300 hover:shadow-lg focus-within:-translate-y-1 dark:border-neutral-800 dark:bg-neutral-900 dark:hover:border-primary-700"
                    initial={reducedMotion ? false : { opacity: 0, y: 16 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, amount: 0.3 }}
                    transition={{ duration: reducedMotion ? 0 : 0.4, delay: reducedMotion ? 0 : index * 0.06 }}
                    tabIndex={0}
                  >
                    <span className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-primary-500/0 blur-2xl transition-colors duration-300 group-hover:bg-primary-500/15" aria-hidden="true" />
                    <span className="relative flex h-11 w-11 items-center justify-center rounded-xl bg-primary-50 text-primary-600 transition-[background-color,color,transform] duration-ui ease-productive group-hover:scale-110 group-hover:bg-primary-600 group-hover:text-white dark:bg-primary-950 dark:text-primary-300">
                      <Icon size={21} aria-hidden="true" />
                    </span>
                    <h3 className="mt-5 font-bold">{department.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-neutral-600 dark:text-neutral-400">{department.text}</p>
                  </motion.article>
                );
              })}
            </div>
          </div>
        </section>

        <section id="security" className="scroll-mt-20 py-20 sm:py-24">
          <div className="app-container grid gap-12 lg:grid-cols-[0.75fr_1.25fr] lg:items-start">
            <motion.div {...reveal}>
              <SectionHeading eyebrow="Trust and control" title="AI assistance without surrendering authority" description="The platform keeps company context, policy evidence, access decisions, and important human checkpoints explicit." align="left" />
              <div className="mt-7 inline-flex items-center gap-2 rounded-xl bg-success-50 px-4 py-3 text-sm font-semibold text-success-800 dark:bg-success-900/20 dark:text-success-300">
                <ShieldCheck size={18} aria-hidden="true" /> Designed for accountable operations
              </div>
            </motion.div>
            <div className="grid gap-4 sm:grid-cols-2">
              {controls.map(([Icon, title, text], index) => (
                <motion.article
                  key={String(title)}
                  className="group rounded-2xl border border-neutral-200 bg-white p-5 transition-[border-color,box-shadow,transform] duration-ui ease-productive hover:-translate-y-0.5 hover:border-primary-200 hover:shadow-card dark:border-neutral-800 dark:bg-neutral-900 dark:hover:border-primary-800"
                  {...reveal}
                  transition={{ duration: reducedMotion ? 0 : 0.45, delay: index * 0.04 }}
                >
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-50 text-primary-600 transition-[background-color,color,transform] duration-ui group-hover:scale-110 group-hover:bg-primary-600 group-hover:text-white dark:bg-primary-950 dark:text-primary-300">
                    <Icon size={20} aria-hidden="true" />
                  </span>
                  <h3 className="mt-4 font-bold">{String(title)}</h3>
                  <p className="mt-2 text-sm leading-6 text-neutral-600 dark:text-neutral-400">{String(text)}</p>
                </motion.article>
              ))}
            </div>
          </div>
        </section>

        <section className="px-4 pb-20 sm:px-6 sm:pb-24">
          <motion.div
            className="gradient-border relative mx-auto max-w-7xl overflow-hidden rounded-3xl bg-primary-600 px-6 py-12 text-center text-white shadow-xl shadow-primary-900/20 sm:px-12 sm:py-16"
            {...reveal}
          >
            <div className="absolute inset-0 bg-gradient-to-br from-primary-500/0 via-violet-500/10 to-sky-500/0 opacity-60" aria-hidden="true" />
            <div className="relative">
              <BadgeCheck className="mx-auto text-primary-100" size={34} aria-hidden="true" />
              <h2 className="mt-5 text-3xl font-bold tracking-tight sm:text-4xl">Create the workspace where coordinated work becomes visible.</h2>
              <p className="mx-auto mt-4 max-w-2xl text-primary-100">Register a Company workspace, configure the departments you need, and activate when your organization is ready.</p>
              <div className="mt-8 flex flex-col justify-center gap-3 min-[420px]:flex-row">
                <Link to="/signup" className="rounded-xl bg-white px-6 py-3 font-semibold text-primary-700 shadow-sm transition-[background-color,box-shadow,transform] duration-ui ease-productive hover:bg-primary-50 hover:shadow-md motion-safe:active:scale-[0.98]">Create workspace</Link>
                <Link to="/login" className="rounded-xl border border-white/30 px-6 py-3 font-semibold transition-[background-color,border-color] duration-ui ease-productive hover:bg-white/10 hover:border-white/40">Sign in</Link>
              </div>
            </div>
          </motion.div>
        </section>
      </main>
      <PublicFooter />
    </div>
  );
}

function ProductPreview({ reducedMotion }: { reducedMotion: boolean }) {
  const cards = [
    ['IT access request', 'Information Technology', 'In progress'],
    ['Equipment budget check', 'Finance collaboration', 'Validated'],
    ['Supplier shortlist', 'Procurement', 'Human selection'],
  ];
  return (
    <motion.div
      className="relative"
      initial={reducedMotion ? false : { opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: reducedMotion ? 0 : 0.65, delay: 0.1 }}
      aria-label="Product workflow preview"
    >
      <div className="rounded-3xl border border-white/10 bg-white/[0.07] p-3 shadow-2xl backdrop-blur sm:p-5">
        <div className="rounded-2xl bg-neutral-900 p-4 ring-1 ring-white/10 sm:p-5">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div>
              <p className="text-xs text-neutral-400">Company workspace</p>
              <p className="mt-1 font-semibold">Operations overview</p>
            </div>
            <span className="inline-flex items-center gap-2 rounded-full bg-success-400/10 px-3 py-1 text-xs font-semibold text-success-300">
              <span className="h-2 w-2 rounded-full bg-success-400 motion-safe:animate-pulse" /> Live
            </span>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2">
            {['12 active', '3 approvals', '98% visible'].map((metric) => (
              <div key={metric} className="rounded-xl bg-white/[0.05] p-3 text-center text-xs text-neutral-300">{metric}</div>
            ))}
          </div>
          <div className="mt-4 space-y-2.5">
            {cards.map(([title, owner, status], index) => (
              <motion.div
                key={title}
                className="group/card flex items-center gap-3 rounded-xl border border-white/[0.07] bg-white/[0.04] p-3 transition-[background-color,border-color,transform] duration-ui ease-productive hover:bg-white/[0.07] hover:border-primary-400/30 motion-safe:hover:translate-x-0.5"
                initial={reducedMotion ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: reducedMotion ? 0 : 0.35, delay: 0.35 + index * 0.1 }}
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-500/15 text-primary-300 transition-colors duration-ui group-hover/card:bg-primary-500/25"><CheckCircle2 size={17} /></span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold">{title}</p>
                  <p className="truncate text-xs text-neutral-400">{owner}</p>
                </div>
                <span className="hidden rounded-full bg-white/[0.07] px-2.5 py-1 text-[11px] text-neutral-300 min-[420px]:block">{status}</span>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
      <div className="absolute -bottom-5 -left-3 hidden items-center gap-3 rounded-xl border border-white/10 bg-neutral-900 px-4 py-3 shadow-xl sm:flex">
        <ShieldCheck size={20} className="text-success-300" />
        <div><p className="text-xs font-semibold">Human control</p><p className="text-[11px] text-neutral-400">Approval requested only when needed</p></div>
      </div>
    </motion.div>
  );
}

function SectionHeading({ eyebrow, title, description, align = 'center' }: { eyebrow: string; title: string; description: string; align?: 'left' | 'center' }) {
  return (
    <div className={align === 'center' ? 'mx-auto max-w-3xl text-center' : 'max-w-xl'}>
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary-600 dark:text-primary-400">{eyebrow}</p>
      <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">{title}</h2>
      <p className="mt-4 text-base leading-7 text-neutral-600 dark:text-neutral-400">{description}</p>
    </div>
  );
}
