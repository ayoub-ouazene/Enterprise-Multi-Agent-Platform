import { CheckCircle2, Circle, Lock } from 'lucide-react';
import type { OnboardingStatusDetailed } from '../../api/types';
import type { StepId } from '../registry';
import { ONBOARDING_STEPS, stepBlocked, stepComplete } from '../registry';

export function WizardProgress({ currentStep, status, onStepClick }: { currentStep: StepId; status: OnboardingStatusDetailed; onStepClick: (step: StepId) => void }) {
  return <nav aria-label="Onboarding steps"><ol className="space-y-1">{ONBOARDING_STEPS.map((step) => {
    const current = currentStep === step.id;
    const complete = stepComplete(step, status);
    const blocked = stepBlocked(step, status);
    const Icon = complete ? CheckCircle2 : blocked ? Lock : Circle;
    return <li key={step.id}><button aria-current={current ? 'step' : undefined} disabled={blocked} onClick={() => onStepClick(step.id)} className={`flex min-h-11 w-full items-start gap-3 rounded-lg px-3 py-2 text-left ${current ? 'bg-primary-50 text-primary-800 dark:bg-primary-950 dark:text-primary-200' : 'hover:bg-neutral-50 dark:hover:bg-neutral-800'} disabled:cursor-not-allowed disabled:opacity-50`}><Icon size={17} className={complete ? 'mt-0.5 text-success-600' : 'mt-0.5 text-neutral-400'} /><span><span className="block text-sm font-semibold">{step.label}{!step.required && <span className="ml-2 text-xs font-normal text-neutral-500">Optional</span>}</span><span className="block text-xs text-neutral-500">{blocked ? 'Complete prerequisite steps first' : step.description}</span></span></button></li>;
  })}</ol></nav>;
}
