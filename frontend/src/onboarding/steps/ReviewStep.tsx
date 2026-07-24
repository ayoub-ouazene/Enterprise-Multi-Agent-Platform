import { CheckCircle2, XCircle, Rocket, ArrowRight } from 'lucide-react';
import type { OnboardingStatusDetailed } from '../../api/types';
import { Button } from '../../components/ui/Button';
import { Alert } from '../../components/ui/Alert';
import type { StepId } from '../registry';
import { getStepByRequirement } from '../registry';
import { ActivationModal } from '../components/ActivationModal';
import { useState } from 'react';

interface ReviewStepProps {
  status: OnboardingStatusDetailed;
  onNavigate: (step: StepId) => void;
  onActivate: () => Promise<void>;
  activating: boolean;
}

export function ReviewStep({ status, onNavigate, onActivate, activating }: ReviewStepProps) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">Review & Activate</h2>
        <p className="text-xs text-neutral-500 dark:text-neutral-400">
          Review all requirements before activating your company.
        </p>
      </div>

      {status.can_activate ? (
        <Alert variant="success" title="Ready to activate">
          All onboarding requirements are satisfied. You can activate your company now.
        </Alert>
      ) : (
        <Alert variant="warning" title="Requirements incomplete">
          Fix the issues below before activating.
        </Alert>
      )}

      <div className="space-y-2">
        {status.items.map((item) => {
          const step = getStepByRequirement(item.requirement);
          return (
            <div
              key={item.requirement}
              className="flex items-center justify-between rounded-lg border border-neutral-200 bg-white p-3 dark:border-neutral-700 dark:bg-neutral-800"
            >
              <div className="flex items-center gap-3">
                {item.satisfied ? (
                  <CheckCircle2 size={18} className="text-success-500" />
                ) : (
                  <XCircle size={18} className="text-danger-500" />
                )}
                <div>
                  <p className={['text-sm font-medium', item.satisfied ? 'text-neutral-500 line-through dark:text-neutral-400' : 'text-neutral-900 dark:text-neutral-100'].join(' ')}>
                    {step?.label ?? item.requirement}
                  </p>
                  {item.details && (
                    <p className="text-xs text-neutral-500 dark:text-neutral-400">{item.details}</p>
                  )}
                </div>
              </div>
              {!item.satisfied && step && (
                <Button size="sm" variant="ghost" onClick={() => onNavigate(step.id)}>
                  <span className="inline-flex items-center gap-1">
                    Fix <ArrowRight size={12} />
                  </span>
                </Button>
              )}
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-end pt-2">
        <Button
          size="lg"
          onClick={() => setModalOpen(true)}
          disabled={!status.can_activate || activating}
          isLoading={activating}
        >
          <span className="inline-flex items-center gap-2">
            <Rocket size={18} />
            Activate Company
          </span>
        </Button>
      </div>

      <ActivationModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onConfirm={async () => {
          await onActivate();
          setModalOpen(false);
        }}
        isActivating={activating}
      />
    </div>
  );
}
