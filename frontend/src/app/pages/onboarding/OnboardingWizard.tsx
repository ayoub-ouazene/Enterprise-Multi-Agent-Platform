import { useEffect, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { ChevronsRight, ChevronsLeft, SkipForward } from 'lucide-react';
import { useOnboardingStatus, useActivateCompany } from '../../../api/hooks/useOnboarding';
import { useAuthContext } from '../../../auth/hooks/useAuthContext';
import { PageContainer } from '../../../components/layout/PageContainer';
import { Skeleton } from '../../../components/layout/Skeleton';
import { Alert } from '../../../components/ui/Alert';
import { Button } from '../../../components/ui/Button';
import type { StepId } from '../../../onboarding/registry';
import { ONBOARDING_STEPS, isValidStepId, getNextStepId, getPreviousStepId } from '../../../onboarding/registry';
import { WizardProgress } from '../../../onboarding/components/WizardProgress';
import { OverviewStep } from '../../../onboarding/steps/OverviewStep';
import { ProfileStep } from '../../../onboarding/steps/ProfileStep';
import { DepartmentsStep } from '../../../onboarding/steps/DepartmentsStep';
import { EmployeesStep } from '../../../onboarding/steps/EmployeesStep';
import { ManagersStep } from '../../../onboarding/steps/ManagersStep';
import { PoliciesStep } from '../../../onboarding/steps/PoliciesStep';
import { OptionalDataStep } from '../../../onboarding/steps/OptionalDataStep';
import { ReviewStep } from '../../../onboarding/steps/ReviewStep';

export function OnboardingWizard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setOnboardingComplete } = useAuthContext();

  const rawStep = searchParams.get('step') ?? '';
  const currentStep: StepId = isValidStepId(rawStep) ? rawStep : 'overview';

  const { data: status, isLoading, error } = useOnboardingStatus();
  const activateMutation = useActivateCompany();

  // Compute first incomplete required step for redirects
  const firstIncomplete = useMemo(() => {
    if (!status) return null;
    const item = status.items.find((i) => !i.satisfied);
    if (!item) return null;
    const step = ONBOARDING_STEPS.find((s) => s.requirementKey === item.requirement);
    return step?.id ?? null;
  }, [status]);

  // Redirect to first incomplete step if current is blocked
  useEffect(() => {
    if (!status || isLoading) return;
    if (!isValidStepId(rawStep)) {
      const target = firstIncomplete ?? 'overview';
      setSearchParams({ step: target }, { replace: true });
    }
  }, [status, isLoading, rawStep, firstIncomplete, setSearchParams]);

  function goTo(step: StepId) {
    setSearchParams({ step }, { replace: true });
  }

  function handleNext() {
    const next = getNextStepId(currentStep);
    if (next) goTo(next);
  }

  function handleBack() {
    const prev = getPreviousStepId(currentStep);
    if (prev) goTo(prev);
  }

  async function handleActivate() {
    await activateMutation.mutateAsync();
    setOnboardingComplete(true);
    navigate('/app/overview', { replace: true });
  }

  const satisfiedSet = useMemo(() => {
    return new Set(status?.items.filter((i) => i.satisfied).map((i) => i.requirement) ?? []);
  }, [status]);

  const isLastStep = currentStep === 'review';
  const isOptional = getStepDef(currentStep)?.optional ?? false;

  if (isLoading) {
    return (
      <PageContainer>
        <div className="mx-auto max-w-5xl">
          <Skeleton variant="rect" className="h-8 w-48 mb-4" />
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[240px_1fr]">
            <Skeleton variant="rect" className="h-96 w-full" />
            <Skeleton variant="rect" className="h-96 w-full" />
          </div>
        </div>
      </PageContainer>
    );
  }

  if (error || !status) {
    return (
      <PageContainer>
        <Alert variant="error" title="Failed to load onboarding status">
          {error instanceof Error ? error.message : 'Please try again later.'}
        </Alert>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="mx-auto max-w-5xl">
        <header className="mb-6">
          <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 sm:text-2xl">
            Company Onboarding
          </h1>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Complete these steps to activate your company.
          </p>
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[240px_1fr]">
          {/* Sidebar */}
          <aside className="hidden lg:block">
            <div className="sticky top-6 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-800">
              <WizardProgress
                currentStep={currentStep}
                completedRequirements={satisfiedSet}
                onStepClick={goTo}
              />
            </div>
          </aside>

          {/* Mobile step indicator */}
          <div className="lg:hidden">
            <select
              value={currentStep}
              onChange={(e) => goTo(e.target.value as StepId)}
              className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 dark:border-neutral-600 dark:bg-neutral-700 dark:text-neutral-100"
            >
              {ONBOARDING_STEPS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          {/* Main content */}
          <main className="space-y-6">
            <section
              key={currentStep}
              className="rounded-lg border border-neutral-200 bg-white p-5 shadow-xs dark:border-neutral-700 dark:bg-neutral-800"
            >
              <StepContent step={currentStep} status={status} onNavigate={goTo} onActivate={handleActivate} activating={activateMutation.isPending} />
            </section>

            {/* Navigation */}
            <div className="flex items-center justify-between">
              <Button variant="secondary" onClick={handleBack} disabled={currentStep === 'overview'}>
                <span className="inline-flex items-center gap-1">
                  <ChevronsLeft size={14} />
                  Back
                </span>
              </Button>

              <div className="flex items-center gap-3">
                {isOptional && (
                  <Button variant="ghost" onClick={handleNext}>
                    <span className="inline-flex items-center gap-1">
                      Skip <SkipForward size={14} />
                    </span>
                  </Button>
                )}
                {!isLastStep && (
                  <Button onClick={handleNext}>
                    <span className="inline-flex items-center gap-1">
                      Next <ChevronsRight size={14} />
                    </span>
                  </Button>
                )}
              </div>
            </div>
          </main>
        </div>
      </div>
    </PageContainer>
  );
}

function getStepDef(id: StepId) {
  return ONBOARDING_STEPS.find((s) => s.id === id);
}

function StepContent({
  step,
  status,
  onNavigate,
  onActivate,
  activating,
}: {
  step: StepId;
  status: import('../../../api/types').OnboardingStatusDetailed;
  onNavigate: (s: StepId) => void;
  onActivate: () => Promise<void>;
  activating: boolean;
}) {
  switch (step) {
    case 'overview':
      return <OverviewStep status={status} onNavigate={onNavigate} />;
    case 'profile':
      return <ProfileStep status={status} />;
    case 'departments':
      return <DepartmentsStep status={status} />;
    case 'employees':
      return <EmployeesStep status={status} />;
    case 'managers':
      return <ManagersStep status={status} />;
    case 'policies':
      return <PoliciesStep status={status} />;
    case 'optional-data':
      return <OptionalDataStep />;
    case 'review':
      return <ReviewStep status={status} onNavigate={onNavigate} onActivate={onActivate} activating={activating} />;
    default:
      return null;
  }
}
