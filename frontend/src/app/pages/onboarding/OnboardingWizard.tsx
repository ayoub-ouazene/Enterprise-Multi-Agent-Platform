import { useEffect, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { CheckCircle2, ChevronLeft, ChevronRight, LogOut, Menu } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { useActivateCompany, useOnboardingStatus } from '../../../api/hooks/useOnboarding';
import { useAuthContext } from '../../../auth/hooks/useAuthContext';
import { Alert } from '../../../components/ui/Alert';
import { Button } from '../../../components/ui/Button';
import { Modal } from '../../../components/ui/Modal';
import { Skeleton } from '../../../components/layout/Skeleton';
import { WizardProgress } from '../../../onboarding/components/WizardProgress';
import { firstIncompleteRoute, getNextStepId, getPreviousStepId, getStepById, isValidStepId, stepBlocked, type StepId } from '../../../onboarding/registry';
import { DepartmentsStep } from '../../../onboarding/steps/DepartmentsStep';
import { EmployeesStep } from '../../../onboarding/steps/EmployeesStep';
import { ManagersStep } from '../../../onboarding/steps/ManagersStep';
import { OptionalDataStep } from '../../../onboarding/steps/OptionalDataStep';
import { OverviewStep } from '../../../onboarding/steps/OverviewStep';
import { PoliciesStep } from '../../../onboarding/steps/PoliciesStep';
import { ProfileStep } from '../../../onboarding/steps/ProfileStep';
import { ReviewStep } from '../../../onboarding/steps/ReviewStep';
import { clearSensitiveSession } from '../../layout/session-cleanup';

export function OnboardingWizard() {
  const { stepId } = useParams();
  const navigate = useNavigate();
  const reducedMotion = useReducedMotion();
  const auth = useAuthContext();
  const statusQuery = useOnboardingStatus();
  const activation = useActivateCompany();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activated, setActivated] = useState(false);
  const current: StepId = isValidStepId(stepId) ? stepId : 'welcome';

  useEffect(() => {
    if (!isValidStepId(stepId)) navigate('/app/onboarding/welcome', { replace: true });
  }, [navigate, stepId]);
  useEffect(() => {
    if (statusQuery.data?.is_active && !activated) navigate('/app/dashboard', { replace: true });
  }, [activated, navigate, statusQuery.data?.is_active]);

  if (statusQuery.isLoading) return <div className="min-h-screen bg-neutral-50 p-6 dark:bg-neutral-950"><div className="mx-auto max-w-6xl"><Skeleton className="h-16" /><Skeleton className="mt-6 h-[32rem]" /></div></div>;
  if (!statusQuery.data) return <div className="min-h-screen p-6"><Alert variant="error" title="Setup unavailable">The onboarding checklist could not be loaded. Check the connection and try again.</Alert></div>;

  const status = statusQuery.data;
  const definition = getStepById(current)!;
  const blocked = stepBlocked(definition, status);
  const go = (step: StepId) => { setDrawerOpen(false); navigate(`/app/onboarding/${step}`); };
  const previous = getPreviousStepId(current);
  const next = getNextStepId(current);

  async function activate() {
    await activation.mutateAsync();
    auth.setOnboardingComplete(true);
    if (auth.user) auth.login({ ...auth.user, company_active: true, onboarding_complete: true });
    setActivated(true);
  }

  if (activated) return <div className="grid min-h-screen place-items-center bg-neutral-50 p-6 dark:bg-neutral-950"><motion.section initial={reducedMotion ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-xl rounded-card border border-success-200 bg-white p-8 text-center shadow-lg dark:border-success-900 dark:bg-neutral-900"><CheckCircle2 className="mx-auto text-success-600" size={48} /><h1 className="mt-4 text-2xl font-bold">Company activated</h1><p className="mt-2 text-neutral-500">Enabled departments and provisioned accounts are now available. Optional data can still be configured from Company Administration.</p><Button className="mt-6" onClick={() => navigate('/app/dashboard', { replace: true })}>Open Company dashboard</Button></motion.section></div>;

  return <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
    <header className="border-b border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900"><div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between px-4 sm:px-6"><div><p className="font-bold">TellUS AI</p><p className="text-xs text-neutral-500">Company setup</p></div><Button variant="ghost" onClick={() => { clearSensitiveSession(auth.logout); navigate('/login', { replace: true }); }}><LogOut size={16} className="mr-2" />Save and exit</Button></div></header>
    <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[280px_minmax(0,1fr)]">
      <aside className="hidden lg:block"><div className="sticky top-6 rounded-card border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900"><p className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">Setup progress</p><WizardProgress currentStep={current} status={status} onStepClick={go} /></div></aside>
      <main id="main-content" className="min-w-0">
        <button className="mb-4 flex min-h-11 w-full items-center justify-between rounded-lg border border-neutral-200 bg-white px-3 text-left lg:hidden dark:border-neutral-800 dark:bg-neutral-900" onClick={() => setDrawerOpen(true)}><span><span className="block text-xs text-neutral-500">Current step</span><strong>{definition.label}</strong></span><Menu /></button>
        <div className="mb-5"><p className="text-xs font-semibold uppercase tracking-wide text-primary-700">Company onboarding</p><h1 className="mt-1 text-2xl font-bold">{definition.label}</h1><p className="mt-1 text-sm text-neutral-500">{definition.description}</p></div>
        <motion.section key={current} initial={reducedMotion ? false : { opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} className="rounded-card border border-neutral-200 bg-white p-5 shadow-xs sm:p-6 dark:border-neutral-800 dark:bg-neutral-900">
          {blocked ? <Alert variant="warning" title="Complete prerequisite steps first">This step uses authoritative setup data from earlier steps. <button className="font-semibold underline" onClick={() => navigate(firstIncompleteRoute(status))}>Open the next required step</button>.</Alert> : <StepContent step={current} status={status} onNavigate={go} onActivate={activate} activating={activation.isPending} />}
        </motion.section>
        <nav aria-label="Wizard navigation" className="mt-5 flex items-center justify-between"><Button variant="secondary" disabled={!previous} onClick={() => previous && go(previous)}><ChevronLeft size={16} className="mr-1" />Back</Button>{next && <Button onClick={() => go(next)}>{definition.required ? 'Continue' : 'Skip or continue'}<ChevronRight size={16} className="ml-1" /></Button>}</nav>
      </main>
    </div>
    <Modal title="Onboarding steps" isOpen={drawerOpen} onClose={() => setDrawerOpen(false)}><WizardProgress currentStep={current} status={status} onStepClick={go} /></Modal>
  </div>;
}

function StepContent({ step, status, onNavigate, onActivate, activating }: { step: StepId; status: import('../../../api/types').OnboardingStatusDetailed; onNavigate: (step: StepId) => void; onActivate: () => Promise<void>; activating: boolean }) {
  switch (step) {
    case 'welcome': return <OverviewStep status={status} onNavigate={onNavigate} />;
    case 'company': return <ProfileStep status={status} />;
    case 'departments': return <DepartmentsStep status={status} />;
    case 'employees': return <EmployeesStep status={status} />;
    case 'managers': return <ManagersStep status={status} />;
    case 'policies': return <PoliciesStep status={status} />;
    case 'optional-data': return <OptionalDataStep />;
    case 'review': return <ReviewStep status={status} onNavigate={onNavigate} onActivate={onActivate} activating={activating} />;
  }
}
