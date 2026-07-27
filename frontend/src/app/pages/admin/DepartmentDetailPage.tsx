import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useAdminDepartments, useAdminEmployees, useAdminPolicyReadiness } from '../../../api/hooks/useAdmin';
import { useManagerCoverage } from '../../../api/hooks/useOnboarding';
import { AdminPageHeader } from '../../../admin/components/AdminPageHeader';
import { AdminCell, AdminRow, AdminTable } from '../../../admin/components/AdminTable';
import { Button } from '../../../components/ui/Button';
import { StatusBadge } from './components/StatusBadge';
import { ErrorState } from './components/ErrorState';

export function DepartmentDetailPage() {
  const { departmentId } = useParams();
  const navigate = useNavigate();
  const departments = useAdminDepartments();
  const members = useAdminEmployees({ department_id: departmentId, limit: 100 });
  const managers = useManagerCoverage();
  const policies = useAdminPolicyReadiness();
  const department = departments.data?.find((item) => item.id === departmentId);
  if (departments.isLoading) return <div className="h-64 animate-pulse rounded-card bg-neutral-200" />;
  if (!department) return <ErrorState message="Department not found in this company." />;
  const manager = managers.data?.find((item) => item.department_id === department.id)?.manager;
  return <div className="space-y-6">
    <Button variant="ghost" size="sm" onClick={() => navigate('/app/admin/departments')}><ArrowLeft size={15} className="mr-2" />Departments</Button>
    <AdminPageHeader title={department.name} description="Safe department membership, leadership, and operational readiness." actions={<StatusBadge status={department.is_active ? 'success' : 'neutral'}>{department.is_active ? 'Enabled' : 'Disabled'}</StatusBadge>} />
    <div className="grid gap-4 sm:grid-cols-3"><Metric label="Manager" value={manager?.employee_code ?? 'Not assigned'} /><Metric label="Active policy" value={policies.data?.department_coverage[department.department_type] ? 'Covered' : 'Missing'} /><Metric label="Members shown" value={String(members.data?.length ?? 0)} /></div>
    <section><h2 className="mb-3 text-base font-semibold">Department members</h2><AdminTable columns={['Employee', 'Title', 'Status', '']} empty={members.data?.length === 0}>{members.data?.map((employee) => <AdminRow key={employee.id}><AdminCell><span className="font-semibold">{employee.employee_code}</span><p className="text-xs text-neutral-500">{employee.email}</p></AdminCell><AdminCell>{employee.job_title ?? 'Not set'}</AdminCell><AdminCell>{employee.employment_status}</AdminCell><AdminCell align="right"><Button variant="ghost" size="sm" onClick={() => navigate(`/app/admin/employees/${employee.id}`)}>Open employee</Button></AdminCell></AdminRow>)}</AdminTable></section>
  </div>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-card border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900"><p className="text-xs font-medium uppercase tracking-wide text-neutral-500">{label}</p><p className="mt-2 font-semibold">{value}</p></div>;
}
