import { useState } from 'react';
import { Boxes, Power } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAdminDepartments, useAdminEmployees, useAdminPolicyReadiness, useUpdateDepartment } from '../../../api/hooks/useAdmin';
import { useManagerCoverage } from '../../../api/hooks/useOnboarding';
import { useAuthContext } from '../../../auth/hooks/useAuthContext';
import { canCreateCompanyWideRecords } from '../../../admin/permissions';
import { AdminPageHeader } from '../../../admin/components/AdminPageHeader';
import { Button } from '../../../components/ui/Button';
import { ConfirmDialog } from '../../../components/ui/ConfirmDialog';
import { Alert } from '../../../components/ui/Alert';
import { StatusBadge } from './components/StatusBadge';
import { TableSkeleton } from './components/TableSkeleton';

export function DepartmentsPage() {
  const { user } = useAuthContext();
  const navigate = useNavigate();
  const departments = useAdminDepartments();
  const employees = useAdminEmployees({ employment_status: 'active', limit: 200 });
  const coverage = useManagerCoverage();
  const policies = useAdminPolicyReadiness();
  const update = useUpdateDepartment();
  const [toggle, setToggle] = useState<{ id: string; name: string; active: boolean; members: number } | null>(null);
  const canEdit = canCreateCompanyWideRecords(user);

  if (departments.isLoading) return <TableSkeleton rows={5} />;
  return <div className="space-y-6">
    <AdminPageHeader title="Departments" description="The five fixed departments define operational ownership. Disabling is blocked while active members remain." />
    {update.isError && <Alert variant="warning">The department change was not applied. Current data has been refreshed.</Alert>}
    <div className="grid gap-4 xl:grid-cols-2">
      {departments.data?.map((department) => {
        const memberCount = employees.data?.filter((employee) => employee.department_id === department.id).length ?? 0;
        const manager = coverage.data?.find((item) => item.department_id === department.id)?.manager;
        const policyReady = policies.data?.department_coverage[department.department_type] ?? false;
        return <article key={department.id} className="rounded-card border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900">
          <div className="flex items-start justify-between gap-4"><div className="flex gap-3"><span className="grid h-10 w-10 place-items-center rounded-lg bg-neutral-100 dark:bg-neutral-800"><Boxes size={18} /></span><div><h2 className="font-semibold">{department.name}</h2><p className="mt-0.5 text-xs uppercase tracking-wide text-neutral-500">{department.department_type.replaceAll('_', ' ')}</p></div></div><StatusBadge status={department.is_active ? 'success' : 'neutral'}>{department.is_active ? 'Enabled' : 'Disabled'}</StatusBadge></div>
          <dl className="mt-5 grid grid-cols-3 gap-3 text-sm"><div><dt className="text-xs text-neutral-500">Members</dt><dd className="mt-1 font-semibold">{memberCount}</dd></div><div><dt className="text-xs text-neutral-500">Manager</dt><dd className="mt-1 truncate font-semibold">{manager?.employee_code ?? 'Missing'}</dd></div><div><dt className="text-xs text-neutral-500">Policy</dt><dd className="mt-1 font-semibold">{policyReady ? 'Ready' : 'Missing'}</dd></div></dl>
          <div className="mt-5 flex gap-2"><Button variant="secondary" className="flex-1" onClick={() => navigate(`/app/admin/departments/${department.id}`)}>View details</Button>{canEdit && <Button variant={department.is_active ? 'danger' : 'primary'} onClick={() => setToggle({ id: department.id, name: department.name, active: department.is_active, members: memberCount })}><Power size={15} className="mr-2" />{department.is_active ? 'Disable' : 'Enable'}</Button>}</div>
        </article>;
      })}
    </div>
    <ConfirmDialog isOpen={Boolean(toggle)} title={`${toggle?.active ? 'Disable' : 'Enable'} ${toggle?.name ?? 'department'}`} message={toggle?.active ? `This stops new operational routing. The backend will reject the change while ${toggle.members} active member(s) remain; manager and history are preserved.` : 'This makes the department available for approved workflows. Manager and policy readiness are still enforced separately.'} confirmLabel={toggle?.active ? 'Disable department' : 'Enable department'} confirmVariant={toggle?.active ? 'danger' : 'primary'} isPending={update.isPending} onCancel={() => setToggle(null)} onConfirm={() => toggle && update.mutate({ id: toggle.id, body: { is_active: !toggle.active } }, { onSuccess: () => setToggle(null), onError: () => { setToggle(null); departments.refetch(); } })} />
  </div>;
}
