import { useMemo, useState, type FormEvent } from 'react';
import { Plus, Search } from 'lucide-react';
import { useAdminSuppliers, useCreateSupplier, useUpdateSupplier } from '../../../api/hooks/useAdmin';
import type { AdminSupplierResponse } from '../../../api/types';
import { AdminPageHeader } from '../../../admin/components/AdminPageHeader';
import { AdminCell, AdminRow, AdminTable } from '../../../admin/components/AdminTable';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Modal } from '../../../components/ui/Modal';
import { Checkbox } from '../../../components/ui/FormControls';
import { ConfirmDialog } from '../../../components/ui/ConfirmDialog';
import { Alert } from '../../../components/ui/Alert';
import { StatusBadge } from './components/StatusBadge';

export function SuppliersPage() {
  const suppliers = useAdminSuppliers({ limit: 100 });
  const [query, setQuery] = useState('');
  const [editing, setEditing] = useState<AdminSupplierResponse | 'create' | null>(null);
  const visible = useMemo(() => suppliers.data?.filter((item) => item.name.toLowerCase().includes(query.toLowerCase())) ?? [], [query, suppliers.data]);
  return <div className="space-y-6">
    <AdminPageHeader title="Supplier directory" description="Maintain safe supplier reference data. This workspace does not shortlist, select, purchase from, pay, or contract with a supplier." actions={<Button onClick={() => setEditing('create')}><Plus size={16} className="mr-2" />Add supplier</Button>} />
    <div className="max-w-sm"><Input label="Search bounded results" value={query} onChange={(event) => setQuery(event.target.value)} icon={<Search size={16} />} /></div>
    {suppliers.isError && <Alert variant="error">Supplier references could not be loaded.</Alert>}
    <AdminTable columns={['Supplier', 'Contact reference', 'Email', 'Phone', 'Status', '']} empty={visible.length === 0}>{visible.map((supplier) => <AdminRow key={supplier.id}><AdminCell><span className="font-semibold">{supplier.name}</span></AdminCell><AdminCell>{supplier.contact_person ?? 'Not set'}</AdminCell><AdminCell>{supplier.email ?? 'Not set'}</AdminCell><AdminCell>{supplier.phone ?? 'Not set'}</AdminCell><AdminCell><StatusBadge status={supplier.is_active ? 'success' : 'neutral'}>{supplier.is_active ? 'Active' : 'Inactive'}</StatusBadge></AdminCell><AdminCell align="right"><Button variant="ghost" size="sm" onClick={() => setEditing(supplier)}>Edit</Button></AdminCell></AdminRow>)}</AdminTable>
    <SupplierModal record={editing === 'create' ? null : editing} open={editing !== null} onClose={() => setEditing(null)} />
  </div>;
}

function SupplierModal({ record, open, onClose }: { record: AdminSupplierResponse | null; open: boolean; onClose: () => void }) {
  const create = useCreateSupplier(); const update = useUpdateSupplier();
  const [confirm, setConfirm] = useState<FormData | null>(null);
  const pending = create.isPending || update.isPending;
  async function apply(data: FormData) {
    const payload = { name: String(data.get('name')), contact_person: String(data.get('contact_person')) || null, email: String(data.get('email')) || null, phone: String(data.get('phone')) || null, website: String(data.get('website')) || null, is_active: data.get('active') === 'on' };
    if (record) await update.mutateAsync({ id: record.id, body: payload }); else await create.mutateAsync(payload);
    setConfirm(null); onClose();
  }
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); if (record?.is_active && data.get('active') !== 'on') setConfirm(data); else void apply(data); }
  return <><Modal title={record ? `Edit ${record.name}` : 'Add supplier reference'} isOpen={open} onClose={onClose}><form className="grid gap-4" onSubmit={submit}><Input name="name" label="Supplier name" defaultValue={record?.name} required /><Input name="contact_person" label="Safe contact reference" defaultValue={record?.contact_person ?? ''} /><Input name="email" type="email" label="Contact email" defaultValue={record?.email ?? ''} /><Input name="phone" label="Contact phone" defaultValue={record?.phone ?? ''} /><Input name="website" type="url" label="Website" defaultValue={record?.website ?? ''} /><Checkbox name="active" label="Active supplier reference" defaultChecked={record?.is_active ?? true} />{(create.isError || update.isError) && <Alert variant="error">The supplier change was rejected. Check for a duplicate name.</Alert>}<div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="submit" isLoading={pending}>Save supplier</Button></div></form></Modal><ConfirmDialog isOpen={Boolean(confirm)} title={`Deactivate ${record?.name ?? 'supplier'}`} message="The supplier will no longer be available for future procurement evaluation. Historical procurement references remain preserved." confirmLabel="Deactivate supplier" confirmVariant="danger" isPending={pending} onCancel={() => setConfirm(null)} onConfirm={() => confirm && void apply(confirm)} /></>;
}
