import { useState } from 'react';
import { Search, ShieldCheck, UserCheck } from 'lucide-react';
import {
  useAssignDepartmentManager,
  useManagerCandidates,
  useManagerCoverage,
} from '../../api/hooks/useOnboarding';
import type { OnboardingStatusDetailed } from '../../api/types';
import { Alert } from '../../components/ui/Alert';
import { Button } from '../../components/ui/Button';
import { Skeleton } from '../../components/layout/Skeleton';

export function ManagersStep({ status }: { status: OnboardingStatusDetailed }) {
  const [departmentId, setDepartmentId] = useState('');
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState('');
  const coverage = useManagerCoverage();
  const candidates = useManagerCandidates(departmentId, query);
  const assign = useAssignDepartmentManager();
  const readiness = status.items.find((item) => item.requirement === 'managers');

  async function confirmAssignment() {
    if (!departmentId || !selected) return;
    await assign.mutateAsync({ departmentId, employeeId: selected });
    setDepartmentId('');
    setQuery('');
    setSelected('');
  }

  return <div className="space-y-6">
    <div>
      <h2 className="text-lg font-semibold">Department managers</h2>
      <p className="mt-1 text-sm text-neutral-500">Assign one active employee to lead each enabled department. The backend grants manager access only after confirmation.</p>
    </div>
    <Alert variant={readiness?.satisfied ? 'success' : 'warning'} title={readiness?.satisfied ? 'Manager coverage complete' : 'Manager coverage required'}>
      {readiness?.details ?? 'Every enabled department needs an authorized manager.'}
    </Alert>
    {coverage.isLoading ? <Skeleton className="h-48" /> : <div className="grid gap-3">
      {coverage.data?.map((item) => <article key={item.department_id} className="rounded-card border border-neutral-200 p-4 dark:border-neutral-800">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-primary-50 text-primary-700 dark:bg-primary-950"><ShieldCheck size={18} /></span>
            <div><h3 className="font-semibold">{item.department_name}</h3><p className="text-sm text-neutral-500">{item.manager ? `${item.manager.employee_code}${item.manager.job_title ? ` · ${item.manager.job_title}` : ''}` : 'No manager assigned'}</p></div>
          </div>
          <Button variant="secondary" onClick={() => { setDepartmentId(item.department_id); setSelected(item.manager?.id ?? ''); }}>{item.manager ? 'Replace manager' : 'Assign manager'}</Button>
        </div>
      </article>)}
    </div>}
    {departmentId && <section className="rounded-card border border-primary-200 bg-primary-50/40 p-4 dark:border-primary-900 dark:bg-primary-950/20" aria-labelledby="manager-search-title">
      <h3 id="manager-search-title" className="font-semibold">Select an eligible employee</h3>
      <label className="mt-3 grid gap-1.5 text-sm font-medium">Search by employee code or job title
        <span className="relative"><Search className="absolute left-3 top-3 text-neutral-400" size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} className="h-11 w-full rounded-lg border border-neutral-300 bg-white pl-9 pr-3 dark:border-neutral-700 dark:bg-neutral-950" /></span>
      </label>
      <fieldset className="mt-3"><legend className="sr-only">Eligible employees</legend><div className="grid max-h-64 gap-2 overflow-y-auto">
        {candidates.data?.map((candidate) => <label key={candidate.id} className="flex min-h-11 items-center gap-3 rounded-lg border bg-white px-3 py-2 dark:border-neutral-700 dark:bg-neutral-900"><input type="radio" name="manager-candidate" value={candidate.id} checked={selected === candidate.id} onChange={() => setSelected(candidate.id)} /><span><strong>{candidate.employee_code}</strong>{candidate.job_title ? ` · ${candidate.job_title}` : ''}{candidate.is_current_manager ? ' · Current manager' : ''}</span></label>)}
        {!candidates.isLoading && candidates.data?.length === 0 && <p className="text-sm text-neutral-500">No active employees match this search.</p>}
      </div></fieldset>
      {assign.isError && <Alert variant="error" className="mt-3">The manager assignment could not be applied. Readiness has been refreshed.</Alert>}
      <div className="mt-4 flex justify-end gap-2"><Button variant="secondary" onClick={() => setDepartmentId('')}>Cancel</Button><Button onClick={confirmAssignment} disabled={!selected} isLoading={assign.isPending}><UserCheck size={16} className="mr-2" />Confirm manager</Button></div>
    </section>}
  </div>;
}
