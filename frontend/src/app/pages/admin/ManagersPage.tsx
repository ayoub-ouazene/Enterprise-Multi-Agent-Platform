import { useState } from 'react';
import { Search, ShieldCheck } from 'lucide-react';
import { useAssignDepartmentManager, useManagerCandidates, useManagerCoverage } from '../../../api/hooks/useOnboarding';
import { AdminPageHeader } from '../../../admin/components/AdminPageHeader';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Modal } from '../../../components/ui/Modal';
import { Alert } from '../../../components/ui/Alert';
import { StatusBadge } from './components/StatusBadge';
import { TableSkeleton } from './components/TableSkeleton';

export function ManagersPage() {
  const coverage = useManagerCoverage();
  const [departmentId, setDepartmentId] = useState('');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState('');
  const candidates = useManagerCandidates(departmentId, search);
  const assign = useAssignDepartmentManager();
  const selectedDepartment = coverage.data?.find((item) => item.department_id === departmentId);

  async function confirm() {
    if (!selected || !departmentId) return;
    await assign.mutateAsync({ departmentId, employeeId: selected });
    await coverage.refetch();
    setDepartmentId('');
    setSelected('');
    setSearch('');
  }

  return <div className="space-y-6">
    <AdminPageHeader title="Department managers" description="Assign one eligible, active employee to each enabled department. Manager authority changes only after backend confirmation." />
    {coverage.isLoading && <TableSkeleton rows={4} />}
    {coverage.isError && <Alert variant="error">Manager coverage could not be loaded.</Alert>}
    <div className="grid gap-4 lg:grid-cols-2">
      {coverage.data?.map((item) => <article key={item.department_id} className="rounded-card border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900">
        <div className="flex items-start justify-between gap-4">
          <div className="flex min-w-0 gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-primary-50 text-primary-700 dark:bg-primary-950"><ShieldCheck size={18} /></span><div><h2 className="font-semibold text-neutral-950 dark:text-white">{item.department_name}</h2><p className="mt-1 text-sm text-neutral-500">{item.manager ? `${item.manager.employee_code} · ${item.manager.job_title ?? 'Manager'}` : 'No manager assigned'}</p></div></div>
          <StatusBadge status={item.manager ? 'success' : 'warning'}>{item.manager ? 'Covered' : 'Required'}</StatusBadge>
        </div>
        <Button variant="secondary" className="mt-5 w-full" onClick={() => { setDepartmentId(item.department_id); setSelected(item.manager?.id ?? ''); }}>{item.manager ? 'Replace manager' : 'Assign manager'}</Button>
      </article>)}
    </div>
    <Modal title={`${selectedDepartment?.manager ? 'Replace' : 'Assign'} ${selectedDepartment?.department_name ?? ''} manager`} isOpen={Boolean(departmentId)} onClose={() => !assign.isPending && setDepartmentId('')}>
      <div className="grid gap-4">
        {selectedDepartment?.manager && <Alert variant="warning" title="Authority will change">The selected employee will receive department-manager access after confirmation. The current manager will be returned to employee access.</Alert>}
        <Input label="Search eligible employees" value={search} onChange={(event) => setSearch(event.target.value)} icon={<Search size={16} />} placeholder="Employee code or title" />
        <fieldset><legend className="text-sm font-medium">Eligible employees</legend><div className="mt-2 grid max-h-64 gap-2 overflow-y-auto">
          {candidates.data?.map((candidate) => <label key={candidate.id} className="flex min-h-12 cursor-pointer items-center gap-3 rounded-lg border border-neutral-200 px-3 dark:border-neutral-700"><input type="radio" name="admin-manager" value={candidate.id} checked={selected === candidate.id} onChange={() => setSelected(candidate.id)} /><span className="text-sm"><strong>{candidate.employee_code}</strong><br /><span className="text-neutral-500">{candidate.job_title ?? 'Employee'}</span></span></label>)}
          {!candidates.isLoading && candidates.data?.length === 0 && <p className="py-4 text-sm text-neutral-500">No eligible employees match.</p>}
        </div></fieldset>
        {assign.isError && <Alert variant="error">The assignment conflicted with current data. Coverage has been refreshed.</Alert>}
        <div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => setDepartmentId('')}>Cancel</Button><Button onClick={confirm} disabled={!selected} isLoading={assign.isPending}>Confirm authority change</Button></div>
      </div>
    </Modal>
  </div>;
}
