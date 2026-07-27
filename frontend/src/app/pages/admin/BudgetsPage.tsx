import { useState, type FormEvent } from 'react';
import { Plus } from 'lucide-react';
import {
  useAdminBudgets,
  useAdminDepartments,
  useCreateBudget,
  useUpdateBudget,
} from '../../../api/hooks/useAdmin';
import type { AdminBudgetResponse } from '../../../api/types';
import { decimalLessThan, formatDecimalMoney } from '../../../admin/decimal';
import { AdminPageHeader } from '../../../admin/components/AdminPageHeader';
import { AdminCell, AdminRow, AdminTable } from '../../../admin/components/AdminTable';
import { Alert } from '../../../components/ui/Alert';
import { Button } from '../../../components/ui/Button';
import { ConfirmDialog } from '../../../components/ui/ConfirmDialog';
import { Select } from '../../../components/ui/FormControls';
import { Input } from '../../../components/ui/Input';
import { Modal } from '../../../components/ui/Modal';
import { StatusBadge } from './components/StatusBadge';
import { TableSkeleton } from './components/TableSkeleton';

export function BudgetsPage() {
  const [department, setDepartment] = useState('');
  const budgets = useAdminBudgets({ department_id: department || undefined, limit: 100 });
  const departments = useAdminDepartments();
  const [editing, setEditing] = useState<AdminBudgetResponse | 'create' | null>(null);

  if (budgets.isLoading) return <TableSkeleton rows={5} />;

  return (
    <div className="space-y-6">
      <AdminPageHeader
        title="Budgets"
        description="Review exact decimal balances and apply deliberate allocation or lifecycle changes. Calculated balances are read-only."
        actions={<Button onClick={() => setEditing('create')}><Plus size={16} className="mr-2" />Create budget</Button>}
      />
      <div className="max-w-sm">
        <Select label="Department" value={department} onChange={(event) => setDepartment(event.target.value)}>
          <option value="">All permitted budgets</option>
          {departments.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </Select>
      </div>
      {budgets.isError && <Alert variant="error">Budget data is unavailable for this permission scope.</Alert>}
      {budgets.data && (
        <AdminTable
          columns={['Budget', 'Period', 'Allocated', 'Reserved', 'Committed', 'Available', 'Status', '']}
          empty={budgets.data.length === 0}
        >
          {budgets.data.map((budget) => (
            <AdminRow key={budget.id}>
              <AdminCell><span className="font-semibold">{budget.name}</span><p className="text-xs text-neutral-500">{budget.budget_type}</p></AdminCell>
              <AdminCell>{budget.period_start} → {budget.period_end}</AdminCell>
              <AdminCell>{formatDecimalMoney(budget.currency, budget.allocated_amount)}</AdminCell>
              <AdminCell>{formatDecimalMoney(budget.currency, budget.reserved_amount)}</AdminCell>
              <AdminCell>{formatDecimalMoney(budget.currency, budget.committed_amount)}</AdminCell>
              <AdminCell><strong>{formatDecimalMoney(budget.currency, budget.available_amount)}</strong></AdminCell>
              <AdminCell><StatusBadge status={budget.status === 'active' ? 'success' : budget.status === 'draft' ? 'neutral' : 'warning'}>{budget.status}</StatusBadge></AdminCell>
              <AdminCell align="right"><Button variant="ghost" size="sm" onClick={() => setEditing(budget)}>Manage</Button></AdminCell>
            </AdminRow>
          ))}
        </AdminTable>
      )}
      <BudgetModal
        record={editing === 'create' ? null : editing}
        open={editing !== null}
        departments={departments.data ?? []}
        onClose={() => setEditing(null)}
      />
    </div>
  );
}

function BudgetModal({
  record,
  open,
  departments,
  onClose,
}: {
  record: AdminBudgetResponse | null;
  open: boolean;
  departments: { id: string; name: string }[];
  onClose: () => void;
}) {
  const create = useCreateBudget();
  const update = useUpdateBudget();
  const [confirmation, setConfirmation] = useState<FormData | null>(null);
  const pending = create.isPending || update.isPending;

  async function apply(data: FormData) {
    const payload = {
      name: String(data.get('name')),
      budget_type: String(data.get('budget_type')),
      currency: String(data.get('currency')).toUpperCase(),
      period_start: String(data.get('period_start')),
      period_end: String(data.get('period_end')),
      allocated_amount: String(data.get('allocated_amount')),
      approval_threshold: String(data.get('approval_threshold')) || null,
      department_id: String(data.get('department_id')) || null,
      status: String(data.get('status')),
    };
    if (record) await update.mutateAsync({ id: record.id, body: { ...payload, version: record.version } });
    else await create.mutateAsync(payload);
    setConfirmation(null);
    onClose();
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const highImpact = Boolean(
      record
      && (
        decimalLessThan(String(data.get('allocated_amount')), record.allocated_amount)
        || String(data.get('status')) !== record.status
      ),
    );
    if (highImpact) setConfirmation(data);
    else void apply(data);
  }

  return (
    <>
      <Modal title={record ? `Manage ${record.name}` : 'Create budget'} isOpen={open} onClose={onClose}>
        <form onSubmit={submit} className="grid gap-4">
          <Input name="name" label="Budget name" defaultValue={record?.name} required />
          <div className="grid gap-3 sm:grid-cols-2">
            <Select name="budget_type" label="Type" defaultValue={record?.budget_type ?? 'department'}>
              {['company', 'department', 'project', 'operational', 'capital'].map((value) => <option key={value}>{value}</option>)}
            </Select>
            <Select name="department_id" label="Department" defaultValue={record?.department_id ?? ''}>
              <option value="">Company-wide</option>
              {departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </Select>
            <Input name="currency" label="Currency" defaultValue={record?.currency ?? 'USD'} minLength={3} maxLength={3} required />
            <Input
              name="allocated_amount"
              label="Allocated amount"
              inputMode="decimal"
              pattern="[0-9]+([.][0-9]{1,2})?"
              defaultValue={record?.allocated_amount ?? ''}
              required
            />
            <Input name="period_start" label="Period start" type="date" defaultValue={record?.period_start} required />
            <Input name="period_end" label="Period end" type="date" defaultValue={record?.period_end} required />
            <Input name="approval_threshold" label="Approval threshold" inputMode="decimal" defaultValue={record?.approval_threshold ?? ''} />
            <Select name="status" label="Status" defaultValue={record?.status ?? 'draft'}>
              {['draft', 'active', 'frozen', 'closed'].map((value) => <option key={value}>{value}</option>)}
            </Select>
          </div>
          {record && (
            <Alert variant="info">
              Reserved {formatDecimalMoney(record.currency, record.reserved_amount)}, committed {formatDecimalMoney(record.currency, record.committed_amount)}, spent {formatDecimalMoney(record.currency, record.spent_amount)}. These balances cannot be edited directly.
            </Alert>
          )}
          {(create.isError || update.isError) && <Alert variant="error">The budget change was rejected or stale. Authoritative balances have been refreshed.</Alert>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={onClose}>Cancel</Button>
            <Button type="submit" isLoading={pending}>Save budget</Button>
          </div>
        </form>
      </Modal>
      <ConfirmDialog
        isOpen={Boolean(confirmation)}
        title="Confirm high-impact budget change"
        message="Allocation reductions and lifecycle changes can block reservations or new spending. The backend will reject values below reserved, committed, and spent totals."
        confirmLabel="Apply budget change"
        confirmVariant="danger"
        isPending={pending}
        onCancel={() => setConfirmation(null)}
        onConfirm={() => confirmation && void apply(confirmation)}
      />
    </>
  );
}
