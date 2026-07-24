import { clsx } from 'clsx';
import { CheckCircle2, Circle, AlertCircle, Lock } from 'lucide-react';
import type { StepId } from '../registry';
import { ONBOARDING_STEPS } from '../registry';

interface WizardProgressProps {
  currentStep: StepId;
  completedRequirements: Set<string>;
  onStepClick: (step: StepId) => void;
}

export function WizardProgress({ currentStep, completedRequirements, onStepClick }: WizardProgressProps) {
  const currentOrder = ONBOARDING_STEPS.find((s) => s.id === currentStep)?.order ?? 0;

  return (
    <nav aria-label="Onboarding steps" className="w-full">
      <div className="space-y-1">
        {ONBOARDING_STEPS.map((step) => {
          const isCurrent = step.id === currentStep;
          const isCompleted = step.requirementKey
            ? completedRequirements.has(step.requirementKey)
            : step.order < currentOrder;
          const isBlocked = step.order > currentOrder && !step.optional;

          let Icon = Circle;
          if (isCompleted) Icon = CheckCircle2;
          else if (isBlocked) Icon = Lock;
          else if (step.requirementKey && !completedRequirements.has(step.requirementKey)) Icon = AlertCircle;

          return (
            <button
              key={step.id}
              onClick={() => !isBlocked && onStepClick(step.id)}
              disabled={isBlocked}
              className={clsx(
                'flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors',
                isCurrent && 'bg-primary-50 text-primary-700 dark:bg-primary-900 dark:text-primary-200',
                !isCurrent && !isBlocked && 'text-neutral-700 hover:bg-neutral-50 dark:text-neutral-300 dark:hover:bg-neutral-800',
                isBlocked && 'cursor-not-allowed text-neutral-400 dark:text-neutral-600'
              )}
              aria-current={isCurrent ? 'step' : undefined}
            >
              <Icon
                size={16}
                className={clsx(
                  'shrink-0',
                  isCompleted && 'text-success-500 dark:text-success-400',
                  isCurrent && 'text-primary-600 dark:text-primary-300',
                  isBlocked && 'text-neutral-400 dark:text-neutral-600'
                )}
                aria-hidden="true"
              />
              <div className="flex-1">
                <span className="font-medium">{step.label}</span>
                {step.optional && (
                  <span className="ml-2 text-xs text-neutral-400 dark:text-neutral-500">(optional)</span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
