import { useEffect, useRef, useState } from 'react';
import { motion, useReducedMotion, AnimatePresence, useInView } from 'framer-motion';
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  FileText,
  Headphones,
  Laptop,
  LockKeyhole,
  Send,
  ShieldCheck,
  Sparkles,
  Users,
} from 'lucide-react';
import { accessibleMotionDuration } from '../../motion/accessibility';

/**
 * Landing-page animated demo simulation.
 *
 * A self-contained, auto-playing "video-like" walkthrough that requires no
 * external video file. When the section scrolls into view it plays a scripted
 * sequence of scenes simulating the real post-sign-in product flow:
 *
 *   1. Sign in
 *   2. Submit a request
 *   3. Router assigns owner department
 *   4. Department agent processes
 *   5. Cross-department collaboration
 *   6. Human approval checkpoint
 *   7. Independent review
 *   8. Delivery with full timeline
 *
 * Features:
 *   - Inline section (not fullscreen modal)
 *   - Blur gradients in the corners
 *   - Scroll-triggered autoplay via useInView
 *   - Progress bar + step captions
 *   - Replay button
 *   - Reduced-motion fallback (static final state)
 *   - Dark-mode support
 */

/* ────────────────────────────────────────────────────────────────────────── */
/* Scene script                                                               */
/* ────────────────────────────────────────────────────────────────────────── */

interface Scene {
  id: number;
  /** Short label shown in the caption bar. */
  label: string;
  /** Longer description shown below the label. */
  description: string;
  /** Icon for the scene badge. */
  icon: typeof Send;
  /** Accent color class for the active scene. */
  accent: string;
  /** Duration this scene stays on screen (ms). */
  duration: number;
}

const SCENES: Scene[] = [
  {
    id: 1,
    label: 'Sign in',
    description: 'Authenticate into your company workspace.',
    icon: LockKeyhole,
    accent: 'text-primary-300',
    duration: 2200,
  },
  {
    id: 2,
    label: 'Submit a request',
    description: '"I need a new laptop for the design team."',
    icon: Send,
    accent: 'text-sky-300',
    duration: 2600,
  },
  {
    id: 3,
    label: 'Router assigns owner',
    description: 'IT takes ownership. Finance will collaborate on budget.',
    icon: ArrowRight,
    accent: 'text-violet-300',
    duration: 2600,
  },
  {
    id: 4,
    label: 'Department processes',
    description: 'IT agent checks inventory and drafts the request.',
    icon: Laptop,
    accent: 'text-emerald-300',
    duration: 2800,
  },
  {
    id: 5,
    label: 'Collaboration',
    description: 'Finance validates the budget with deterministic balances.',
    icon: Users,
    accent: 'text-amber-300',
    duration: 2800,
  },
  {
    id: 6,
    label: 'Human approval',
    description: 'Manager reviews pre-summarized evidence and approves.',
    icon: ShieldCheck,
    accent: 'text-rose-300',
    duration: 2600,
  },
  {
    id: 7,
    label: 'Independent review',
    description: 'A reviewer checks the result before delivery.',
    icon: CheckCircle2,
    accent: 'text-teal-300',
    duration: 2400,
  },
  {
    id: 8,
    label: 'Delivered',
    description: 'Outcome returned with a full workflow timeline.',
    icon: Sparkles,
    accent: 'text-primary-300',
    duration: 3200,
  },
];

const TOTAL_DURATION = SCENES.reduce((sum, s) => sum + s.duration, 0);

/* ────────────────────────────────────────────────────────────────────────── */
/* Component                                                                   */
/* ────────────────────────────────────────────────────────────────────────── */

export function DemoVideoSection() {
  const reducedMotion = useReducedMotion();
  const sectionRef = useRef<HTMLDivElement>(null);
  const inView = useInView(sectionRef, { once: false, amount: 0.35 });
  const [activeScene, setActiveScene] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // Auto-play when scrolled into view (unless reduced motion).
  useEffect(() => {
    if (reducedMotion) {
      setActiveScene(SCENES.length - 1);
      return;
    }
    if (inView) {
      setIsPlaying(true);
    }
  }, [inView, reducedMotion]);

  // Scene sequencing with automatic loop.
  useEffect(() => {
    if (!isPlaying || reducedMotion) return;
    if (activeScene >= SCENES.length) {
      // Loop back to the beginning
      setActiveScene(0);
      return;
    }
    const timer = setTimeout(() => {
      setActiveScene((prev) => prev + 1);
    }, SCENES[activeScene].duration);
    return () => clearTimeout(timer);
  }, [isPlaying, activeScene, reducedMotion]);

  const elapsed = SCENES.slice(0, activeScene).reduce((sum, s) => sum + s.duration, 0);
  const progress = Math.min(100, (elapsed / TOTAL_DURATION) * 100);
  const current = SCENES[Math.min(activeScene, SCENES.length - 1)];
  const CurrentIcon = current.icon;

  const reveal = {
    initial: reducedMotion ? { opacity: 1 } : { opacity: 0, y: 24 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, amount: 0.2 },
    transition: { duration: accessibleMotionDuration(reducedMotion, 0.6) },
  };

  return (
    <section id="demo" className="scroll-mt-20 py-20 sm:py-24">
      <motion.div className="app-container" {...reveal}>
        <div className="mx-auto max-w-3xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary-200 bg-primary-50 px-3 py-1.5 text-sm font-semibold text-primary-700 dark:border-primary-800 dark:bg-primary-950 dark:text-primary-300">
            <Sparkles size={15} aria-hidden="true" /> Product walkthrough
          </div>
          <h2 className="mt-5 text-3xl font-bold tracking-tight sm:text-4xl">
            See Orchestra in action
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-neutral-600 dark:text-neutral-400">
            Watch a complete request flow — from submission, through routing and collaboration,
            to human approval and delivery.
          </p>
        </div>

        {/* ── Simulated video frame ─────────────────────────────────────── */}
        <div ref={sectionRef} className="relative mx-auto mt-12 max-w-5xl">
          {/* Blur gradients in the corners */}
          <div
            className="pointer-events-none absolute -left-16 -top-16 h-64 w-64 rounded-full bg-primary-500/20 blur-3xl"
            aria-hidden="true"
          />
          <div
            className="pointer-events-none absolute -bottom-16 -right-16 h-72 w-72 rounded-full bg-violet-500/20 blur-3xl"
            aria-hidden="true"
          />
          <div
            className="pointer-events-none absolute -right-20 top-1/3 h-56 w-56 rounded-full bg-sky-500/10 blur-3xl"
            aria-hidden="true"
          />

          {/* Browser chrome frame */}
          <div className="relative overflow-hidden rounded-2xl border border-neutral-200 bg-neutral-950 shadow-2xl dark:border-neutral-800">
            {/* Title bar */}
            <div className="flex items-center gap-2 border-b border-white/10 bg-neutral-900 px-4 py-3">
              <span className="h-3 w-3 rounded-full bg-red-400/80" aria-hidden="true" />
              <span className="h-3 w-3 rounded-full bg-amber-400/80" aria-hidden="true" />
              <span className="h-3 w-3 rounded-full bg-emerald-400/80" aria-hidden="true" />
              <div className="ml-3 flex-1">
                <div className="mx-auto max-w-md truncate rounded-md bg-white/5 px-3 py-1 text-center text-xs text-neutral-400">
                  orchestra.app/requests
                </div>
              </div>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-success-400/10 px-2.5 py-1 text-[11px] font-semibold text-success-300">
                <span className="h-1.5 w-1.5 rounded-full bg-success-400 motion-safe:animate-pulse" />
                Live demo
              </span>
            </div>

            {/* Stage */}
            <div className="relative aspect-video w-full bg-neutral-950">
              <AnimatePresence mode="wait">
                <SceneStage key={current.id} scene={current} reducedMotion={Boolean(reducedMotion)} />
              </AnimatePresence>
            </div>

            {/* Caption bar */}
            <div className="border-t border-white/10 bg-neutral-900/90 px-5 py-4 backdrop-blur">
              <div className="flex items-center gap-3">
                <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/10 ${current.accent}`}>
                  <CurrentIcon size={18} aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <AnimatePresence mode="wait">
                    <motion.p
                      key={`label-${current.id}`}
                      className="text-sm font-semibold text-white"
                      initial={reducedMotion ? false : { opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={reducedMotion ? { opacity: 0 } : { opacity: 0, y: -6 }}
                      transition={{ duration: accessibleMotionDuration(reducedMotion, 0.25) }}
                    >
                      {current.label}
                    </motion.p>
                  </AnimatePresence>
                  <AnimatePresence mode="wait">
                    <motion.p
                      key={`desc-${current.id}`}
                      className="truncate text-xs text-neutral-400"
                      initial={reducedMotion ? false : { opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={reducedMotion ? { opacity: 0 } : { opacity: 0 }}
                      transition={{ duration: accessibleMotionDuration(reducedMotion, 0.25) }}
                    >
                      {current.description}
                    </motion.p>
                  </AnimatePresence>
                </div>
              </div>

              {/* Progress bar */}
              <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-white/10">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-primary-500 to-violet-400"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: accessibleMotionDuration(reducedMotion, 0.4), ease: 'easeOut' }}
                />
              </div>
            </div>
          </div>

          {/* Step indicators below the frame */}
          <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
            {SCENES.map((scene, i) => {
              const isActive = i === Math.min(activeScene, SCENES.length - 1);
              const isDone = i < activeScene;
              return (
                <div
                  key={scene.id}
                  className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium transition ${
                    isActive
                      ? 'bg-primary-600 text-white'
                      : isDone
                        ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300'
                        : 'bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-500'
                  }`}
                >
                  {isDone && !isActive ? (
                    <CheckCircle2 size={11} aria-hidden="true" />
                  ) : (
                    <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
                  )}
                  <span className="hidden sm:inline">{scene.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      </motion.div>
    </section>
  );
}

/* ────────────────────────────────────────────────────────────────────────── */
/* Per-scene visual stages                                                     */
/* ────────────────────────────────────────────────────────────────────────── */

function SceneStage({ scene, reducedMotion }: { scene: Scene; reducedMotion: boolean }) {
  const base = {
    initial: reducedMotion ? { opacity: 1 } : { opacity: 0 },
    animate: { opacity: 1 },
    exit: reducedMotion ? { opacity: 0 } : { opacity: 0 },
    transition: { duration: accessibleMotionDuration(reducedMotion, 0.4) },
  };

  return (
    <motion.div className="absolute inset-0" {...base}>
      {scene.id === 1 && <SignInStage reducedMotion={reducedMotion} />}
      {scene.id === 2 && <SubmitStage reducedMotion={reducedMotion} />}
      {scene.id === 3 && <RouteStage reducedMotion={reducedMotion} />}
      {scene.id === 4 && <ProcessStage reducedMotion={reducedMotion} />}
      {scene.id === 5 && <CollaborateStage reducedMotion={reducedMotion} />}
      {scene.id === 6 && <ApprovalStage reducedMotion={reducedMotion} />}
      {scene.id === 7 && <ReviewStage reducedMotion={reducedMotion} />}
      {scene.id === 8 && <DeliverStage reducedMotion={reducedMotion} />}
    </motion.div>
  );
}

/* Shared layout helpers ---------------------------------------------------- */

function StageShell({ children, badge }: { children: React.ReactNode; badge: React.ReactNode }) {
  return (
    <div className="flex h-full w-full flex-col">
      <div className="flex items-center gap-2 border-b border-white/5 px-5 py-3">
        {badge}
        <span className="text-xs text-neutral-500">Orchestra workspace</span>
      </div>
      <div className="flex-1 overflow-hidden p-5">{children}</div>
    </div>
  );
}

function TypingLine({ text, delay = 0, reducedMotion }: { text: string; delay?: number; reducedMotion: boolean }) {
  if (reducedMotion) return <span>{text}</span>;
  return (
    <motion.span
      initial={{ width: 0 }}
      whileInView={{ width: '100%' }}
      viewport={{ once: true }}
      transition={{ duration: 1.2, delay, ease: 'easeOut' }}
      style={{ display: 'inline-block', overflow: 'hidden', whiteSpace: 'nowrap', verticalAlign: 'bottom' }}
    >
      {text}
    </motion.span>
  );
}

/* Scene 1: Sign in --------------------------------------------------------- */

function SignInStage({ reducedMotion }: { reducedMotion: boolean }) {
  return (
    <StageShell badge={<LockKeyhole size={14} className="text-primary-300" />}>
      <div className="flex h-full items-center justify-center">
        <motion.div
          className="w-full max-w-sm rounded-2xl border border-white/10 bg-white/[0.04] p-6"
          initial={reducedMotion ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: accessibleMotionDuration(reducedMotion, 0.5) }}
        >
          <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-primary-600 text-white">
            <LockKeyhole size={22} aria-hidden="true" />
          </div>
          <div className="space-y-3">
            <div>
              <div className="mb-1.5 text-[11px] text-neutral-400">Work email</div>
              <div className="h-9 rounded-lg border border-white/10 bg-white/5 px-3 text-sm text-neutral-300">
                <TypingLine text="alex@northwind.co" delay={0.3} reducedMotion={reducedMotion} />
              </div>
            </div>
            <div>
              <div className="mb-1.5 text-[11px] text-neutral-400">Password</div>
              <div className="h-9 rounded-lg border border-white/10 bg-white/5 px-3 text-sm text-neutral-300">
                <span className="tracking-widest">••••••••••</span>
              </div>
            </div>
            <motion.div
              className="flex h-10 items-center justify-center rounded-lg bg-primary-600 text-sm font-semibold text-white"
              initial={reducedMotion ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: accessibleMotionDuration(reducedMotion, 1.4) }}
            >
              Sign in
            </motion.div>
          </div>
        </motion.div>
      </div>
    </StageShell>
  );
}

/* Scene 2: Submit a request ----------------------------------------------- */

function SubmitStage({ reducedMotion }: { reducedMotion: boolean }) {
  return (
    <StageShell badge={<Send size={14} className="text-sky-300" />}>
      <div className="mx-auto max-w-lg">
        <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-neutral-500">
          New request
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
          <div className="mb-3 flex items-center gap-2 text-sm text-neutral-300">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-sky-500/20 text-xs font-bold text-sky-300">A</span>
            <span>Alex Rivera</span>
          </div>
          <div className="rounded-lg bg-neutral-900 p-3 text-sm leading-6 text-neutral-200">
            <TypingLine text="I need a new laptop for the design team — minimum 32GB RAM." delay={0.2} reducedMotion={reducedMotion} />
          </div>
          <motion.div
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-semibold text-white"
            initial={reducedMotion ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: accessibleMotionDuration(reducedMotion, 1.6) }}
          >
            <Send size={12} aria-hidden="true" /> Submit
          </motion.div>
        </div>
      </div>
    </StageShell>
  );
}

/* Scene 3: Router assigns owner ------------------------------------------- */

function RouteStage({ reducedMotion }: { reducedMotion: boolean }) {
  const departments = [
    { name: 'Customer Support', icon: Headphones, match: false },
    { name: 'Human Resources', icon: Users, match: false },
    { name: 'Information Technology', icon: Laptop, match: true },
    { name: 'Finance', icon: Users, match: false, collaborator: true },
    { name: 'Procurement', icon: Laptop, match: false },
  ];
  return (
    <StageShell badge={<ArrowRight size={14} className="text-violet-300" />}>
      <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-neutral-500">
        Router — selecting owner
      </div>
      <div className="space-y-2">
        {departments.map((dept, i) => {
          const Icon = dept.icon;
          return (
            <motion.div
              key={dept.name}
              className={`flex items-center gap-3 rounded-lg border p-3 text-sm ${
                dept.match
                  ? 'border-violet-400/40 bg-violet-500/10'
                  : dept.collaborator
                    ? 'border-amber-400/30 bg-amber-500/5'
                    : 'border-white/10 bg-white/[0.03]'
              }`}
              initial={reducedMotion ? false : { opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: accessibleMotionDuration(reducedMotion, i * 0.15) }}
            >
              <Icon size={16} className={dept.match ? 'text-violet-300' : 'text-neutral-500'} />
              <span className={dept.match ? 'font-semibold text-white' : 'text-neutral-400'}>
                {dept.name}
              </span>
              <span className="ml-auto text-xs">
                {dept.match && (
                  <span className="rounded-full bg-violet-500/20 px-2 py-0.5 font-semibold text-violet-300">Owner</span>
                )}
                {dept.collaborator && (
                  <span className="rounded-full bg-amber-500/20 px-2 py-0.5 font-semibold text-amber-300">Collaborator</span>
                )}
              </span>
            </motion.div>
          );
        })}
      </div>
    </StageShell>
  );
}

/* Scene 4: Department processes -------------------------------------------- */

function ProcessStage({ reducedMotion }: { reducedMotion: boolean }) {
  const steps = [
    'Reading company hardware policy…',
    'Checking current inventory…',
    'Validating 32GB RAM requirement…',
    'Drafting access request…',
  ];
  return (
    <StageShell badge={<Laptop size={14} className="text-emerald-300" />}>
      <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-neutral-500">
        <Laptop size={14} className="text-emerald-300" /> IT department — processing
      </div>
      <div className="space-y-2.5">
        {steps.map((step, i) => (
          <motion.div
            key={step}
            className="flex items-center gap-2.5 rounded-lg bg-white/[0.04] px-3 py-2 text-sm text-neutral-300"
            initial={reducedMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: accessibleMotionDuration(reducedMotion, i * 0.4) }}
          >
            <motion.span
              className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-300"
              initial={reducedMotion ? false : { scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: accessibleMotionDuration(reducedMotion, i * 0.4 + 0.2) }}
            >
              <CheckCircle2 size={12} aria-hidden="true" />
            </motion.span>
            {step}
          </motion.div>
        ))}
      </div>
    </StageShell>
  );
}

/* Scene 5: Collaboration -------------------------------------------------- */

function CollaborateStage({ reducedMotion }: { reducedMotion: boolean }) {
  return (
    <StageShell badge={<Users size={14} className="text-amber-300" />}>
      <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-neutral-500">
        Cross-department collaboration
      </div>
      <div className="space-y-3">
        <motion.div
          className="rounded-lg border border-emerald-400/20 bg-emerald-500/5 p-3"
          initial={reducedMotion ? false : { opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: accessibleMotionDuration(reducedMotion, 0.4) }}
        >
          <div className="mb-1 text-xs font-semibold text-emerald-300">IT → Finance</div>
          <div className="text-sm text-neutral-300">"Please validate budget for a 32GB laptop (est. $2,400)."</div>
        </motion.div>
        <motion.div
          className="rounded-lg border border-amber-400/20 bg-amber-500/5 p-3"
          initial={reducedMotion ? false : { opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: accessibleMotionDuration(reducedMotion, 0.4), delay: accessibleMotionDuration(reducedMotion, 0.5) }}
        >
          <div className="mb-1 text-xs font-semibold text-amber-300">Finance → IT</div>
          <div className="text-sm text-neutral-300">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={14} className="text-amber-300" />
              Budget available: $5,000 in Q3 equipment allocation
            </div>
          </div>
        </motion.div>
      </div>
    </StageShell>
  );
}

/* Scene 6: Human approval -------------------------------------------------- */

function ApprovalStage({ reducedMotion }: { reducedMotion: boolean }) {
  return (
    <StageShell badge={<ShieldCheck size={14} className="text-rose-300" />}>
      <div className="mx-auto max-w-md">
        <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-neutral-500">
          Approval required
        </div>
        <motion.div
          className="rounded-xl border border-rose-400/30 bg-rose-500/5 p-4"
          initial={reducedMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: accessibleMotionDuration(reducedMotion, 0.4) }}
        >
          <div className="mb-3 flex items-center gap-2">
            <ShieldCheck size={18} className="text-rose-300" />
            <span className="text-sm font-semibold text-white">Manager approval</span>
          </div>
          <div className="space-y-1.5 text-xs text-neutral-400">
            <div className="flex justify-between"><span>Item</span><span className="text-neutral-200">Laptop 32GB</span></div>
            <div className="flex justify-between"><span>Est. cost</span><span className="text-neutral-200">$2,400</span></div>
            <div className="flex justify-between"><span>Budget</span><span className="text-emerald-300">Available</span></div>
            <div className="flex justify-between"><span>Policy</span><span className="text-neutral-200">Compliant</span></div>
          </div>
          <motion.div
            className="mt-4 flex h-9 items-center justify-center rounded-lg bg-emerald-600 text-sm font-semibold text-white"
            initial={reducedMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: accessibleMotionDuration(reducedMotion, 1) }}
          >
            <CheckCircle2 size={15} className="mr-1.5" /> Approve
          </motion.div>
        </motion.div>
      </div>
    </StageShell>
  );
}

/* Scene 7: Independent review ---------------------------------------------- */

function ReviewStage({ reducedMotion }: { reducedMotion: boolean }) {
  return (
    <StageShell badge={<CheckCircle2 size={14} className="text-teal-300" />}>
      <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-neutral-500">
        Independent review
      </div>
      <motion.div
        className="rounded-xl border border-teal-400/20 bg-teal-500/5 p-4"
        initial={reducedMotion ? false : { opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: accessibleMotionDuration(reducedMotion, 0.4) }}
      >
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
          <CheckCircle2 size={16} className="text-teal-300" /> Reviewer checklist
        </div>
        <div className="space-y-2">
          {['Policy compliance verified', 'Budget validated by Finance', 'Inventory confirmed'].map((item, i) => (
            <motion.div
              key={item}
              className="flex items-center gap-2 text-sm text-neutral-300"
              initial={reducedMotion ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: accessibleMotionDuration(reducedMotion, i * 0.3) }}
            >
              <CheckCircle2 size={14} className="text-teal-300" /> {item}
            </motion.div>
          ))}
        </div>
        <motion.div
          className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white"
          initial={reducedMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: accessibleMotionDuration(reducedMotion, 1.2) }}
        >
          <CheckCircle2 size={12} /> Review passed
        </motion.div>
      </motion.div>
    </StageShell>
  );
}

/* Scene 8: Delivered ------------------------------------------------------- */

function DeliverStage({ reducedMotion }: { reducedMotion: boolean }) {
  const timeline = [
    { label: 'Submitted', icon: Send, color: 'text-sky-300' },
    { label: 'Routed to IT', icon: ArrowRight, color: 'text-violet-300' },
    { label: 'Processed', icon: Laptop, color: 'text-emerald-300' },
    { label: 'Finance validated', icon: Users, color: 'text-amber-300' },
    { label: 'Approved', icon: ShieldCheck, color: 'text-rose-300' },
    { label: 'Reviewed', icon: CheckCircle2, color: 'text-teal-300' },
    { label: 'Delivered', icon: Sparkles, color: 'text-primary-300' },
  ];
  return (
    <StageShell badge={<Sparkles size={14} className="text-primary-300" />}>
      <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-neutral-500">
        <FileText size={14} /> Request #REQ-2049 — delivered
      </div>
      <motion.div
        className="mb-4 rounded-xl border border-primary-400/20 bg-primary-500/5 p-4"
        initial={reducedMotion ? false : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: accessibleMotionDuration(reducedMotion, 0.4) }}
      >
        <div className="flex items-center gap-2 text-sm font-semibold text-white">
          <CheckCircle2 size={16} className="text-primary-300" /> Laptop request approved and ordered
        </div>
        <div className="mt-1 text-xs text-neutral-400">32GB unit from Q3 budget · PO #4421 · ETA 3 business days</div>
      </motion.div>
      <div className="space-y-1.5">
        {timeline.map((step, i) => {
          const Icon = step.icon;
          return (
            <motion.div
              key={step.label}
              className="flex items-center gap-2.5 text-sm"
              initial={reducedMotion ? false : { opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: accessibleMotionDuration(reducedMotion, i * 0.12) }}
            >
              <Icon size={14} className={step.color} />
              <span className="text-neutral-300">{step.label}</span>
              <span className="ml-auto text-xs text-neutral-600">
                <Clock size={11} className="inline" /> {`${i * 3 + 1}m ago`}
              </span>
            </motion.div>
          );
        })}
      </div>
    </StageShell>
  );
}

export default DemoVideoSection;
