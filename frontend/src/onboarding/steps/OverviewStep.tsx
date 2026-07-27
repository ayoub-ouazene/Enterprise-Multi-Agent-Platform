import { ArrowRight, CheckCircle2, Circle, RotateCcw } from 'lucide-react';
import { useAdminCompany } from '../../api/hooks/useAdmin';
import type { OnboardingStatusDetailed } from '../../api/types';
import { Button } from '../../components/ui/Button';
import type { StepId } from '../registry';
import { firstIncompleteRoute, ONBOARDING_STEPS, stepComplete } from '../registry';

export function OverviewStep({ status, onNavigate }: { status: OnboardingStatusDetailed; onNavigate: (step: StepId) => void }) {
  const company = useAdminCompany();
  const required = ONBOARDING_STEPS.filter((step) => step.required);
  const completed = required.filter((step) => stepComplete(step, status)).length;
  const next = firstIncompleteRoute(status).split('/').pop() as StepId;
  return <div className="space-y-7">
    <section className="overflow-hidden rounded-card bg-gradient-to-br from-primary-950 to-primary-700 p-6 text-white sm:p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary-200">Workspace setup</p>
      <h2 className="mt-3 text-2xl font-bold">Welcome to {company.data?.name ?? 'your Company workspace'}</h2>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-primary-100">Configure your fixed departments, provision employees, assign managers, and add policy coverage. Progress is saved by the backend and can be resumed safely.</p>
      <div className="mt-6 flex flex-wrap items-center gap-3"><Button onClick={() => onNavigate(next)}>{completed ? 'Continue setup' : 'Start setup'}<ArrowRight size={16} className="ml-2" /></Button><span className="inline-flex items-center gap-2 text-sm text-primary-100"><RotateCcw size={15} />Resume after signing back in</span></div>
    </section>
    <section><div className="flex items-center justify-between"><h3 className="font-semibold">Setup overview</h3><span className="text-sm text-neutral-500">{completed} of {required.length} required checks complete</span></div><ol className="mt-3 grid gap-3 sm:grid-cols-2">{required.map((step) => { const done = stepComplete(step, status); return <li key={step.id} className="flex gap-3 rounded-card border border-neutral-200 p-4 dark:border-neutral-800">{done ? <CheckCircle2 className="shrink-0 text-success-600" size={19} /> : <Circle className="shrink-0 text-neutral-400" size={19} />}<div><p className="font-semibold">{step.label}</p><p className="text-sm text-neutral-500">{step.description}</p></div></li>; })}</ol></section>
    <p className="text-sm text-neutral-500">Employees and managers receive access only through controlled provisioning. Company activation remains unavailable until every required backend readiness check passes.</p>
  </div>;
}
