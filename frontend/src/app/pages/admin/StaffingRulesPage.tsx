import { useState, type FormEvent } from 'react';
import { Plus } from 'lucide-react';
import { useAdminDepartments, useAdminStaffingRules, useCreateStaffingRule, useUpdateStaffingRule } from '../../../api/hooks/useAdmin';
import type { AdminStaffingRuleResponse } from '../../../api/types';
import { AdminPageHeader } from '../../../admin/components/AdminPageHeader';
import { AdminCell, AdminRow, AdminTable } from '../../../admin/components/AdminTable';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Modal } from '../../../components/ui/Modal';
import { Checkbox, Select } from '../../../components/ui/FormControls';
import { ConfirmDialog } from '../../../components/ui/ConfirmDialog';
import { Alert } from '../../../components/ui/Alert';
import { StatusBadge } from './components/StatusBadge';

export function StaffingRulesPage() {
  const [department, setDepartment] = useState('');
  const rules = useAdminStaffingRules({ department_id: department || undefined, limit: 100 });
  const departments = useAdminDepartments();
  const [editing, setEditing] = useState<AdminStaffingRuleResponse | 'create' | null>(null);
  return <div className="space-y-6">
    <AdminPageHeader title="Staffing rules" description="Define effective minimum staffing for leave validation. Changes do not retroactively alter approved leave." actions={<Button onClick={() => setEditing('create')}><Plus size={16} className="mr-2" />Add rule</Button>} />
    <div className="max-w-sm"><Select label="Department" value={department} onChange={(event) => setDepartment(event.target.value)}><option value="">All departments</option>{departments.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></div>
    {rules.isError && <Alert variant="error">Staffing rules could not be loaded.</Alert>}
    <AdminTable columns={['Department', 'Minimum active', 'Effective period', 'Status', '']} empty={rules.data?.length === 0}>{rules.data?.map((rule) => <AdminRow key={rule.id}><AdminCell><span className="font-semibold">{departments.data?.find((item) => item.id === rule.department_id)?.name ?? 'Department'}</span></AdminCell><AdminCell>{rule.minimum_active_employees}</AdminCell><AdminCell>{rule.effective_from} → {rule.effective_to ?? 'Ongoing'}</AdminCell><AdminCell><StatusBadge status={rule.is_active ? 'success' : 'neutral'}>{rule.is_active ? 'Active' : 'Inactive'}</StatusBadge></AdminCell><AdminCell align="right"><Button variant="ghost" size="sm" onClick={() => setEditing(rule)}>Edit</Button></AdminCell></AdminRow>)}</AdminTable>
    <StaffingModal record={editing === 'create' ? null : editing} departments={departments.data ?? []} open={editing !== null} onClose={() => setEditing(null)} />
  </div>;
}

function StaffingModal({ record, departments, open, onClose }: { record: AdminStaffingRuleResponse | null; departments: { id: string; name: string }[]; open: boolean; onClose: () => void }) {
  const create = useCreateStaffingRule(); const update = useUpdateStaffingRule();
  const [confirm, setConfirm] = useState<FormData | null>(null);
  async function apply(data: FormData) {
    const payload = { department_id: String(data.get('department_id')), minimum_active_employees: Number(data.get('minimum_active_employees')), effective_from: String(data.get('effective_from')), effective_to: String(data.get('effective_to')) || null, is_active: data.get('active') === 'on' };
    if (record) await update.mutateAsync({ id: record.id, body: payload }); else await create.mutateAsync(payload);
    setConfirm(null); onClose();
  }
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); if (record?.is_active && data.get('active') !== 'on') setConfirm(data); else void apply(data); }
  const pending = create.isPending || update.isPending;
  return <><Modal title={record ? 'Edit staffing rule' : 'Add staffing rule'} isOpen={open} onClose={onClose}><form className="grid gap-4" onSubmit={submit}><Select name="department_id" label="Department" defaultValue={record?.department_id ?? ''} disabled={Boolean(record)} required><option value="">Select department</option>{departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select><Input name="minimum_active_employees" label="Minimum active employees" type="number" min={0} defaultValue={record?.minimum_active_employees ?? 0} required /><div className="grid gap-3 sm:grid-cols-2"><Input name="effective_from" label="Effective from" type="date" defaultValue={record?.effective_from} required /><Input name="effective_to" label="Effective to" type="date" defaultValue={record?.effective_to ?? ''} /></div><Checkbox name="active" label="Active staffing rule" defaultChecked={record?.is_active ?? true} />{(create.isError || update.isError) && <Alert variant="error">The period is invalid or overlaps an existing active rule.</Alert>}<div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="submit" isLoading={pending}>Save staffing rule</Button></div></form></Modal><ConfirmDialog isOpen={Boolean(confirm)} title="Deactivate staffing rule" message="Future leave validation will no longer use this rule. Existing approved leave remains unchanged." confirmLabel="Deactivate rule" confirmVariant="danger" isPending={pending} onCancel={() => setConfirm(null)} onConfirm={() => confirm && void apply(confirm)} /></>;
}
