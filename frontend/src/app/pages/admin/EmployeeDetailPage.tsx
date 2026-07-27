import { useEffect, useState, type FormEvent } from 'react';
import { ArrowLeft, ShieldAlert } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAdminDepartments, useAdminEmployee, useAdminEmployees, useDeactivateEmployee, useUpdateEmployee } from '../../../api/hooks/useAdmin';
import { useAuthContext } from '../../../auth/hooks/useAuthContext';
import { canCreateCompanyWideRecords } from '../../../admin/permissions';
import { AdminPageHeader } from '../../../admin/components/AdminPageHeader';
import { Button } from '../../../components/ui/Button';
import { ConfirmDialog } from '../../../components/ui/ConfirmDialog';
import { Input } from '../../../components/ui/Input';
import { Select } from '../../../components/ui/FormControls';
import { Alert } from '../../../components/ui/Alert';
import { StatusBadge } from './components/StatusBadge';
import { ErrorState } from './components/ErrorState';

export function EmployeeDetailPage() {
  const { employeeId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuthContext();
  const employee = useAdminEmployee(employeeId);
  const departments = useAdminDepartments();
  const candidates = useAdminEmployees({ department_id: employee.data?.department_id ?? undefined, employment_status: 'active', limit: 100 });
  const update = useUpdateEmployee();
  const deactivate = useDeactivateEmployee();
  const [editing, setEditing] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [message, setMessage] = useState('');
  const canDeactivate = canCreateCompanyWideRecords(user);

  useEffect(() => setEditing(false), [employeeId]);
  if (employee.isLoading) return <div className="h-64 animate-pulse rounded-card bg-neutral-200 dark:bg-neutral-800" />;
  if (employee.isError || !employee.data) return <ErrorState message="Employee detail is unavailable or outside your permitted scope." />;
  const record = employee.data;

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setMessage('');
    try {
      await update.mutateAsync({ id: record.id, body: {
        employee_code: String(form.get('employee_code')),
        email: String(form.get('email')),
        job_title: String(form.get('job_title')) || null,
        department_id: String(form.get('department_id')) || null,
        manager_employee_id: String(form.get('manager_employee_id')) || null,
        employment_status: String(form.get('employment_status')),
      } });
      await employee.refetch();
      setEditing(false);
      setMessage('Employee changes were confirmed by the server.');
    } catch {
      setMessage('The update was not applied. Authoritative data has been refreshed.');
      await employee.refetch();
    }
  }

  return <div className="space-y-6">
    <Button variant="ghost" size="sm" onClick={() => navigate('/app/admin/employees')}><ArrowLeft size={15} className="mr-2" />Employee directory</Button>
    <AdminPageHeader title={record.employee_code} description={record.email ?? 'Provisioned employee record'} actions={<><Button variant="secondary" onClick={() => setEditing((value) => !value)}>{editing ? 'Cancel edit' : 'Edit employee'}</Button>{canDeactivate && record.employment_status === 'active' && <Button variant="danger" onClick={() => setConfirm(true)}>Deactivate</Button>}</>} />
    {message && <Alert variant={message.startsWith('Employee') ? 'success' : 'warning'}>{message}</Alert>}
    <form onSubmit={save} className="grid gap-5 rounded-card border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex flex-wrap gap-2"><StatusBadge status={record.employment_status === 'active' ? 'success' : 'neutral'}>{record.employment_status}</StatusBadge>{record.must_change_password && <StatusBadge status="warning">First login password change required</StatusBadge>}{record.actor_type === 'department_manager' && <StatusBadge status="info">Department manager</StatusBadge>}</div>
      <div className="grid gap-4 sm:grid-cols-2"><Input name="employee_code" label="Employee code" defaultValue={record.employee_code} disabled={!editing} /><Input name="email" type="email" label="Work email" defaultValue={record.email ?? ''} disabled={!editing} /><Input name="job_title" label="Job title" defaultValue={record.job_title ?? ''} disabled={!editing} /><Select name="department_id" label="Department" defaultValue={record.department_id ?? ''} disabled={!editing}><option value="">Unassigned</option>{departments.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select><Select name="manager_employee_id" label="Reports to" defaultValue={record.manager_employee_id ?? ''} disabled={!editing}><option value="">No reporting manager</option>{candidates.data?.filter((item) => item.id !== record.id).map((item) => <option key={item.id} value={item.id}>{item.employee_code} — {item.job_title ?? 'Employee'}</option>)}</Select><Select name="employment_status" label="Employment status" defaultValue={record.employment_status} disabled={!editing}><option value="active">Active</option><option value="inactive">Inactive</option><option value="on_leave">On leave</option></Select></div>
      {editing && <div className="flex justify-end"><Button type="submit" isLoading={update.isPending}>Save confirmed changes</Button></div>}
    </form>
    <ConfirmDialog isOpen={confirm} title={`Deactivate ${record.employee_code}`} message="Access will be disabled only after the backend confirms there is no department-manager role, assigned asset, or pending HumanAction. Existing history is preserved." confirmLabel="Deactivate employee" confirmVariant="danger" isPending={deactivate.isPending} onCancel={() => setConfirm(false)} onConfirm={() => deactivate.mutate(record.id, { onSuccess: () => { setConfirm(false); navigate('/app/admin/employees'); }, onError: async () => { setConfirm(false); setMessage('Deactivation was blocked. Resolve the employee responsibilities shown by the server and retry.'); await employee.refetch(); } })} />
    {deactivate.isError && <Alert variant="warning"><ShieldAlert size={16} className="mr-2 inline" />Deactivation was not applied.</Alert>}
  </div>;
}
