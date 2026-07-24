import { CheckCircle2, Circle, AlertCircle, ArrowRight } from 'lucide-react';
import type { OnboardingStatusDetailed } from '../../api/types';
import type { StepId } from '../registry';
import { ONBOARDING_STEPS } from '../registry';

interface OverviewStepProps {
  status: OnboardingStatusDetailed;
  onNavigate: (step: StepId) => void;
}

export function OverviewStep({ status, onNavigate }: OverviewStepProps) {
  const totalRequired = ONBOARDING_STEPS.filter((s) => s.requirementKey).length;
  const completedCount = status.items.filter((i) => i.satisfied).length;
  const progressPct = Math.round((completedCount / totalRequired) * 100);

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-neutral-200 bg-white p-5 dark:border-neutral-700 dark:bg-neutral-800">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
              Onboarding Progress
            </h2>
            <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
              {completedCount} of {totalRequired} required steps completed
            </p>
          </div>
          <div className="text-right">
            <span className="text-2xl font-bold text-primary-600 dark:text-primary-400">
              {progressPct}%
            </span>
          </div>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-700">
          <div
            className="h-full rounded-full bg-primary-500 transition-all"
            style={{ width: `${progressPct}%` }}
            aria-hidden="true"
          />
        </div>
        {status.can_activate && (
          <div className="mt-4 flex items-center gap-2 rounded-md bg-success-50 p-3 text-sm text-success-800 dark:bg-success-900/30 dark:text-success-200">
            <CheckCircle2 size={16} />
            All requirements met. You can activate your company in the Review step.
          </div>
        )}
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">Steps</h3>
        <div className="divide-y divide-neutral-100 rounded-lg border border-neutral-200 bg-white dark:divide-neutral-700 dark:border-neutral-700 dark:bg-neutral-800">
          {ONBOARDING_STEPS.filter((s) => s.requirementKey).map((step) => {
            const item = status.items.find((i) => i.requirement === step.requirementKey);
            const satisfied = item?.satisfied ?? false;
            return (
              <button
                key={step.id}
                onClick={() => onNavigate(step.id)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-neutral-50 dark:hover:bg-neutral-800/50"
              >
                {satisfied ? (
                  <CheckCircle2 size={18} className="shrink-0 text-success-500" />
                ) : (
                  <Circle size={18} className="shrink-0 text-neutral-400" />
                )}
                <div className="flex-1">
                  <p className={['text-sm font-medium', satisfied ? 'text-neutral-500 dark:text-neutral-400 line-through' : 'text-neutral-900 dark:text-neutral-100'].join(' ')}>
                    {step.label}
                  </p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400">{step.description}</p>
                </div>
                {!satisfied && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-warning-100 px-2 py-0.5 text-xs font-medium text-warning-700 dark:bg-warning-900 dark:text-warning-300">
                    <AlertCircle size={10} />
                    Required
                  </span>
                )}
                <ArrowRight size={14} className="text-neutral-400" />
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
