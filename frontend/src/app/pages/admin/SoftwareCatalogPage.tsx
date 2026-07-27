import { useState, type FormEvent } from 'react';
import { Plus } from 'lucide-react';
import { useAdminSoftwareCatalog, useCreateSoftware, useUpdateSoftware } from '../../../api/hooks/useAdmin';
import type { AdminSoftwareCatalogResponse } from '../../../api/types';
import { AdminPageHeader } from '../../../admin/components/AdminPageHeader';
import { AdminCell, AdminRow, AdminTable } from '../../../admin/components/AdminTable';
import { Button } from '../../../components/ui/Button';
import { Modal } from '../../../components/ui/Modal';
import { Input } from '../../../components/ui/Input';
import { Checkbox, Select } from '../../../components/ui/FormControls';
import { ConfirmDialog } from '../../../components/ui/ConfirmDialog';
import { Alert } from '../../../components/ui/Alert';
import { StatusBadge } from './components/StatusBadge';
import { TableSkeleton } from './components/TableSkeleton';

export function SoftwareCatalogPage() {
  const catalog = useAdminSoftwareCatalog({ limit: 100 });
  const [editing, setEditing] = useState<AdminSoftwareCatalogResponse | 'create' | null>(null);
  if (catalog.isLoading) return <TableSkeleton rows={5} />;
  return <div className="space-y-6">
    <AdminPageHeader title="Software catalogue" description="Manage approved reference data and available licence capacity. Access is still granted only through authorized workflows." actions={<Button onClick={() => setEditing('create')}><Plus size={16} className="mr-2" />Add software</Button>} />
    {catalog.isError && <Alert variant="error">The software catalogue could not be loaded.</Alert>}
    {catalog.data && <AdminTable columns={['Software', 'Access', 'Approvals', 'Available capacity', 'Status', '']} empty={catalog.data.length === 0}>{catalog.data.map((record) => <AdminRow key={record.id}><AdminCell><span className="font-semibold">{record.name}</span></AdminCell><AdminCell>{record.access_type}</AdminCell><AdminCell>{[record.requires_manager_approval && 'Manager', record.requires_it_approval && 'IT'].filter(Boolean).join(' + ') || 'None'}</AdminCell><AdminCell>{record.license_limited ? record.available_license_count ?? 0 : 'Unlimited'}</AdminCell><AdminCell><StatusBadge status={record.is_active ? 'success' : 'neutral'}>{record.is_active ? 'Active' : 'Inactive'}</StatusBadge></AdminCell><AdminCell align="right"><Button variant="ghost" size="sm" onClick={() => setEditing(record)}>Edit</Button></AdminCell></AdminRow>)}</AdminTable>}
    <SoftwareModal record={editing === 'create' ? null : editing} open={editing !== null} onClose={() => setEditing(null)} />
  </div>;
}

function SoftwareModal({ record, open, onClose }: { record: AdminSoftwareCatalogResponse | null; open: boolean; onClose: () => void }) {
  const create = useCreateSoftware();
  const update = useUpdateSoftware();
  const [confirm, setConfirm] = useState<FormData | null>(null);
  async function submitData(data: FormData) {
    const payload = {
      name: String(data.get('name')), access_type: String(data.get('access_type')),
      requires_manager_approval: data.get('manager') === 'on', requires_it_approval: data.get('it') === 'on',
      license_limited: data.get('limited') === 'on',
      available_license_count: data.get('limited') === 'on' ? Number(data.get('available')) : null,
      is_active: data.get('active') === 'on',
    };
    if (record) await update.mutateAsync({ id: record.id, body: { ...payload, version: record.version } });
    else await create.mutateAsync(payload);
    setConfirm(null); onClose();
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const reduction = record?.available_license_count != null && Number(data.get('available')) < record.available_license_count;
    const deactivate = record?.is_active && data.get('active') !== 'on';
    if (reduction || deactivate) setConfirm(data); else void submitData(data);
  }
  const pending = create.isPending || update.isPending;
  return <><Modal title={record ? `Edit ${record.name}` : 'Add software reference'} isOpen={open} onClose={onClose}><form className="grid gap-4" onSubmit={submit}><Input name="name" label="Software name" defaultValue={record?.name} required /><Select name="access_type" label="Access type" defaultValue={record?.access_type ?? 'licensed'}><option value="licensed">Licensed</option><option value="role_based">Role based</option><option value="open">Open</option></Select><div className="grid gap-1"><Checkbox name="manager" label="Manager approval required" defaultChecked={record?.requires_manager_approval} /><Checkbox name="it" label="IT approval required" defaultChecked={record?.requires_it_approval ?? true} /><Checkbox name="limited" label="Licence capacity is limited" defaultChecked={record?.license_limited} /><Checkbox name="active" label="Active in catalogue" defaultChecked={record?.is_active ?? true} /></div><Input name="available" label="Available licence capacity" type="number" min={0} defaultValue={record?.available_license_count ?? 0} helperText="Backend validation remains authoritative. This field does not grant access." />{(create.isError || update.isError) && <Alert variant="error">The change conflicted with current catalogue state. Refresh and retry.</Alert>}<div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="submit" isLoading={pending}>Save catalogue entry</Button></div></form></Modal><ConfirmDialog isOpen={Boolean(confirm)} title={`Confirm high-impact software change`} message="Reducing available capacity or deactivating this entry can block future access workflows. Existing access is not revoked by this catalogue change." confirmLabel="Apply confirmed change" confirmVariant="danger" isPending={pending} onCancel={() => setConfirm(null)} onConfirm={() => confirm && void submitData(confirm)} /></>;
}
