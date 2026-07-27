import { useState, type FormEvent } from 'react';
import { ArrowLeft } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAdminAsset, useAdminEmployees, useRetireAsset, useUpdateAsset } from '../../../api/hooks/useAdmin';
import { AdminPageHeader } from '../../../admin/components/AdminPageHeader';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Select } from '../../../components/ui/FormControls';
import { ConfirmDialog } from '../../../components/ui/ConfirmDialog';
import { Alert } from '../../../components/ui/Alert';
import { StatusBadge } from './components/StatusBadge';
import { ErrorState } from './components/ErrorState';

export function AssetDetailPage() {
  const { assetId } = useParams();
  const navigate = useNavigate();
  const asset = useAdminAsset(assetId);
  const [employeeQuery, setEmployeeQuery] = useState('');
  const employees = useAdminEmployees({ q: employeeQuery || undefined, employment_status: 'active', limit: 25 });
  const update = useUpdateAsset();
  const retire = useRetireAsset();
  const [confirmRetire, setConfirmRetire] = useState(false);
  const [message, setMessage] = useState('');
  if (asset.isLoading) return <div className="h-64 animate-pulse rounded-card bg-neutral-200" />;
  if (asset.isError || !asset.data) return <ErrorState message="Asset not found or outside your authorized IT scope." />;
  const record = asset.data;
  const readOnly = record.status === 'retired';

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const assignedEmployeeId = String(form.get('assigned_employee_id')) || null;
    const selectedStatus = String(form.get('status'));
    const status = assignedEmployeeId
      ? 'assigned'
      : selectedStatus === 'assigned'
        ? 'available'
        : selectedStatus;
    setMessage('');
    try {
      await update.mutateAsync({ id: record.id, body: { version: record.version, status, assigned_employee_id: assignedEmployeeId, location: String(form.get('location')) || null } });
      setMessage('Asset state was confirmed by the server. Physical delivery, if needed, remains a separate human action.');
      await asset.refetch();
    } catch {
      setMessage('The asset changed concurrently or violated an assignment rule. Current data has been refreshed.');
      await asset.refetch();
    }
  }
  return <div className="space-y-6">
    <Button variant="ghost" size="sm" onClick={() => navigate('/app/admin/assets')}><ArrowLeft size={15} className="mr-2" />Asset inventory</Button>
    <AdminPageHeader title={record.asset_code} description={`${record.brand} ${record.model} · version ${record.version}`} actions={<StatusBadge status={record.status === 'available' ? 'success' : record.status === 'assigned' ? 'info' : 'neutral'}>{record.status}</StatusBadge>} />
    {message && <Alert variant={message.startsWith('Asset state') ? 'success' : 'warning'}>{message}</Alert>}
    <form onSubmit={save} className="grid gap-4 rounded-card border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="grid gap-4 sm:grid-cols-2"><Input label="Type" value={record.asset_type} disabled /><Input label="Serial reference" value={record.serial_number ?? 'Not set'} disabled /><Input name="location" label="Location" defaultValue={record.location ?? ''} disabled={readOnly} /><Select name="status" label="Inventory status" defaultValue={record.status} disabled={readOnly}><option value="available">Available</option><option value="assigned">Assigned</option><option value="reserved">Reserved</option><option value="maintenance">Maintenance</option><option value="lost">Lost</option></Select></div>
      <Input label="Find employee for assignment" value={employeeQuery} onChange={(event) => setEmployeeQuery(event.target.value)} disabled={readOnly} placeholder="Code, email, or title" />
      <Select name="assigned_employee_id" label="Assigned employee" defaultValue={record.assigned_employee_id ?? ''} disabled={readOnly}><option value="">No assignee</option>{employees.data?.map((employee) => <option key={employee.id} value={employee.id}>{employee.employee_code} — {employee.job_title ?? employee.email}</option>)}</Select>
      {!readOnly && <div className="flex flex-wrap justify-between gap-2"><Button type="button" variant="danger" onClick={() => setConfirmRetire(true)}>Retire asset</Button><Button type="submit" isLoading={update.isPending}>Confirm inventory change</Button></div>}
    </form>
    <ConfirmDialog isOpen={confirmRetire} title={`Retire ${record.asset_code}`} message="Retirement preserves asset history and makes the asset permanently unavailable for assignment. The backend will reject retirement until any assignee is removed." confirmLabel="Retire asset" confirmVariant="danger" isPending={retire.isPending} onCancel={() => setConfirmRetire(false)} onConfirm={() => retire.mutate(record.id, { onSuccess: () => { setConfirmRetire(false); navigate('/app/admin/assets'); }, onError: async () => { setConfirmRetire(false); setMessage('Retirement was blocked. Unassign the asset and refresh before retrying.'); await asset.refetch(); } })} />
  </div>;
}
