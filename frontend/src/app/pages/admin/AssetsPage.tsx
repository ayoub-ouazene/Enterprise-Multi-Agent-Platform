import { useState, type FormEvent } from 'react';
import { HardDrive, Plus, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAdminAssets, useCreateAsset } from '../../../api/hooks/useAdmin';
import { AdminPageHeader } from '../../../admin/components/AdminPageHeader';
import { AdminCell, AdminRow, AdminTable } from '../../../admin/components/AdminTable';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Modal } from '../../../components/ui/Modal';
import { Select } from '../../../components/ui/FormControls';
import { StatusBadge } from './components/StatusBadge';
import { TableSkeleton } from './components/TableSkeleton';
import { Alert } from '../../../components/ui/Alert';

export function AssetsPage() {
  const navigate = useNavigate();
  const [type, setType] = useState('');
  const [status, setStatus] = useState('');
  const [creating, setCreating] = useState(false);
  const assets = useAdminAssets({ asset_type: type || undefined, asset_status: status || undefined, limit: 100 });
  return <div className="space-y-6">
    <AdminPageHeader title="Asset inventory" description="Maintain authoritative inventory state. Assignment records responsibility; it does not claim physical delivery." actions={<Button onClick={() => setCreating(true)}><Plus size={16} className="mr-2" />Create asset</Button>} />
    <div className="grid gap-3 rounded-card border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900 sm:grid-cols-2">
      <Input label="Asset type" value={type} onChange={(event) => setType(event.target.value)} icon={<Search size={16} />} placeholder="Laptop, monitor…" />
      <Select label="Status" value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All statuses</option>{['available', 'assigned', 'reserved', 'maintenance', 'retired', 'lost'].map((value) => <option key={value}>{value}</option>)}</Select>
    </div>
    {assets.isLoading && <TableSkeleton rows={6} />}
    {assets.isError && <Alert variant="error">Asset inventory could not be loaded for this permission scope.</Alert>}
    {assets.data && <AdminTable columns={['Asset', 'Type', 'Model', 'Assignee', 'Status', 'Location', '']} empty={assets.data.length === 0}>{assets.data.map((asset) => <AdminRow key={asset.id} onClick={() => navigate(`/app/admin/assets/${asset.id}`)}><AdminCell><div className="flex items-center gap-2"><HardDrive size={15} /><span className="font-semibold">{asset.asset_code}</span></div><p className="text-xs text-neutral-500">{asset.serial_number ? `Serial …${asset.serial_number.slice(-4)}` : 'No serial reference'}</p></AdminCell><AdminCell>{asset.asset_type}</AdminCell><AdminCell>{asset.brand} {asset.model}</AdminCell><AdminCell>{asset.assigned_employee_id ? 'Assigned employee' : 'None'}</AdminCell><AdminCell><StatusBadge status={asset.status === 'available' ? 'success' : asset.status === 'assigned' ? 'info' : asset.status === 'retired' ? 'neutral' : 'warning'}>{asset.status}</StatusBadge></AdminCell><AdminCell>{asset.location ?? 'Not set'}</AdminCell><AdminCell align="right"><Button variant="ghost" size="sm" onClick={(event) => { event.stopPropagation(); navigate(`/app/admin/assets/${asset.id}`); }}>Manage</Button></AdminCell></AdminRow>)}</AdminTable>}
    <CreateAssetModal open={creating} onClose={() => setCreating(false)} />
  </div>;
}

function CreateAssetModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const create = useCreateAsset();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await create.mutateAsync({ asset_code: String(form.get('asset_code')), asset_type: String(form.get('asset_type')), brand: String(form.get('brand')), model: String(form.get('model')), serial_number: String(form.get('serial_number')) || null, location: String(form.get('location')) || null, status: 'available' });
    event.currentTarget.reset();
    onClose();
  }
  return <Modal title="Create inventory asset" isOpen={open} onClose={onClose}><form className="grid gap-4" onSubmit={submit}><div className="grid gap-3 sm:grid-cols-2"><Input name="asset_code" label="Asset code" required /><Input name="asset_type" label="Asset type" required /><Input name="brand" label="Brand" required /><Input name="model" label="Model" required /></div><Input name="serial_number" label="Serial reference" /><Input name="location" label="Location" />{create.isError && <Alert variant="error">The asset could not be created. Check duplicate code or serial references.</Alert>}<div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="submit" isLoading={create.isPending}>Create available asset</Button></div></form></Modal>;
}
