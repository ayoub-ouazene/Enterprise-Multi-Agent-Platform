import { useState, type FormEvent } from 'react';
import { Plus, Search, UserRound } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  useAdminDepartments, useAdminEmployees, useCreateEmployee,
} from '../../../api/hooks/useAdmin';
import { useAuthContext } from '../../../auth/hooks/useAuthContext';
import { canCreateCompanyWideRecords } from '../../../admin/permissions';
import { AdminPageHeader } from '../../../admin/components/AdminPageHeader';
import { AdminCell, AdminRow, AdminTable } from '../../../admin/components/AdminTable';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Modal } from '../../../components/ui/Modal';
import { Select } from '../../../components/ui/FormControls';
import { StatusBadge } from './components/StatusBadge';
import { ErrorState } from './components/ErrorState';
import { TableSkeleton } from './components/TableSkeleton';

const pageSize = 25;

export function EmployeeDirectoryPage() {
  const { user } = useAuthContext();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [department, setDepartment] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(0);
  const [creating, setCreating] = useState(false);
  const employees = useAdminEmployees({
    q: search || undefined,
    department_id: department || undefined,
    employment_status: status || undefined,
    limit: pageSize,
    offset: page * pageSize,
  });
  const departments = useAdminDepartments();

  return <div className="space-y-6">
    <AdminPageHeader
      title="Employees"
      description="Provision accounts, review reporting context, and manage employment status without exposing credentials."
      actions={canCreateCompanyWideRecords(user) ? <Button onClick={() => setCreating(true)}><Plus size={16} className="mr-2" />Create employee</Button> : undefined}
    />
    <div className="grid gap-3 rounded-card border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900 sm:grid-cols-3">
      <Input label="Search" value={search} onChange={(event) => { setSearch(event.target.value); setPage(0); }} icon={<Search size={16} />} placeholder="Code, email, or title" />
      <Select label="Department" value={department} onChange={(event) => { setDepartment(event.target.value); setPage(0); }}>
        <option value="">All permitted departments</option>
        {departments.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
      </Select>
      <Select label="Employment status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(0); }}>
        <option value="">All statuses</option><option value="active">Active</option><option value="inactive">Inactive</option><option value="on_leave">On leave</option><option value="terminated">Terminated</option>
      </Select>
    </div>
    {employees.isLoading && <TableSkeleton rows={6} />}
    {employees.isError && <ErrorState message="Employee records could not be loaded." />}
    {employees.data && <AdminTable columns={['Employee', 'Department', 'Title', 'Account', 'Status', '']} empty={employees.data.length === 0}>
      {employees.data.map((employee) => {
        const dept = departments.data?.find((item) => item.id === employee.department_id);
        return <AdminRow key={employee.id} onClick={() => navigate(`/app/admin/employees/${employee.id}`)}>
          <AdminCell><div className="flex items-center gap-3"><span className="grid h-9 w-9 place-items-center rounded-full bg-neutral-100 dark:bg-neutral-800"><UserRound size={16} /></span><div><p className="font-semibold text-neutral-950 dark:text-white">{employee.employee_code}</p><p className="text-xs text-neutral-500">{employee.email ?? 'Account not provisioned'}</p></div></div></AdminCell>
          <AdminCell>{dept?.name ?? 'Unassigned'}</AdminCell>
          <AdminCell>{employee.job_title ?? 'Not set'}</AdminCell>
          <AdminCell>{employee.must_change_password ? 'Password change required' : employee.account_active ? 'Ready' : 'Inactive'}</AdminCell>
          <AdminCell><StatusBadge status={employee.employment_status === 'active' ? 'success' : 'neutral'}>{employee.employment_status.replaceAll('_', ' ')}</StatusBadge></AdminCell>
          <AdminCell align="right"><Button variant="ghost" size="sm" onClick={(event) => { event.stopPropagation(); navigate(`/app/admin/employees/${employee.id}`); }}>Open</Button></AdminCell>
        </AdminRow>;
      })}
    </AdminTable>}
    <div className="flex items-center justify-end gap-2">
      <Button variant="secondary" disabled={page === 0} onClick={() => setPage((value) => value - 1)}>Previous</Button>
      <span className="text-sm text-neutral-500">Page {page + 1}</span>
      <Button variant="secondary" disabled={(employees.data?.length ?? 0) < pageSize} onClick={() => setPage((value) => value + 1)}>Next</Button>
    </div>
    <CreateEmployeeModal open={creating} onClose={() => setCreating(false)} departments={departments.data ?? []} />
  </div>;
}

function CreateEmployeeModal({ open, onClose, departments }: { open: boolean; onClose: () => void; departments: { id: string; name: string; is_active: boolean }[] }) {
  const create = useCreateEmployee();
  const [error, setError] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    const form = new FormData(event.currentTarget);
    try {
      await create.mutateAsync({
        employee_code: String(form.get('employee_code')),
        email: String(form.get('email')),
        temporary_password: String(form.get('temporary_password')),
        job_title: String(form.get('job_title')) || null,
        department_id: String(form.get('department_id')) || null,
        hire_date: String(form.get('hire_date')) || null,
      });
      event.currentTarget.reset();
      onClose();
    } catch {
      setError('The employee was not created. Check for duplicate account details and retry.');
    }
  }

  return <Modal title="Create employee account" isOpen={open} onClose={() => !create.isPending && onClose()}>
    <form className="grid gap-4" onSubmit={submit} autoComplete="off">
      <p className="text-sm text-neutral-600 dark:text-neutral-400">The temporary password is sent only to the backend for hashing and is cleared when this dialog closes.</p>
      <div className="grid gap-3 sm:grid-cols-2"><Input name="employee_code" label="Employee code" required /><Input name="email" label="Work email" type="email" required /></div>
      <Input name="job_title" label="Job title" />
      <Select name="department_id" label="Department" required><option value="">Select an active department</option>{departments.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select>
      <Input name="hire_date" label="Hire date" type="date" />
      <Input name="temporary_password" label="Temporary password" type="password" minLength={12} required autoComplete="new-password" helperText="The employee must change this password on first login." />
      {error && <p role="alert" className="text-sm text-danger-600">{error}</p>}
      <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="submit" isLoading={create.isPending}>Create employee</Button></div>
    </form>
  </Modal>;
}
