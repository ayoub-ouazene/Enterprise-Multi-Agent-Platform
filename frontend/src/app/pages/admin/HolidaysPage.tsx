import { useState, type FormEvent } from 'react';
import { Plus } from 'lucide-react';
import { useAdminHolidays, useCreateHoliday, useUpdateHoliday } from '../../../api/hooks/useAdmin';
import type { AdminHolidayResponse } from '../../../api/types';
import { AdminPageHeader } from '../../../admin/components/AdminPageHeader';
import { AdminCell, AdminRow, AdminTable } from '../../../admin/components/AdminTable';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Modal } from '../../../components/ui/Modal';
import { Checkbox, Select } from '../../../components/ui/FormControls';
import { Alert } from '../../../components/ui/Alert';
import { StatusBadge } from './components/StatusBadge';

export function HolidaysPage() {
  const [year, setYear] = useState(new Date().getFullYear());
  const holidays = useAdminHolidays({ year, limit: 200 });
  const [editing, setEditing] = useState<AdminHolidayResponse | 'create' | null>(null);
  return <div className="space-y-6">
    <AdminPageHeader title="Company holidays" description="Maintain the workday calendar used by deterministic leave calculations. Existing leave outcomes are not rewritten." actions={<Button onClick={() => setEditing('create')}><Plus size={16} className="mr-2" />Add holiday</Button>} />
    <div className="max-w-48"><Select label="Calendar year" value={year} onChange={(event) => setYear(Number(event.target.value))}>{[year - 1, year, year + 1].map((value) => <option key={value} value={value}>{value}</option>)}</Select></div>
    {holidays.isError && <Alert variant="error">The holiday calendar could not be loaded.</Alert>}
    <AdminTable columns={['Date', 'Holiday', 'Paid', '']} empty={holidays.data?.length === 0}>{holidays.data?.map((holiday) => <AdminRow key={holiday.id}><AdminCell><span className="font-semibold">{holiday.holiday_date}</span></AdminCell><AdminCell>{holiday.name}</AdminCell><AdminCell><StatusBadge status={holiday.is_paid ? 'success' : 'neutral'}>{holiday.is_paid ? 'Paid' : 'Unpaid'}</StatusBadge></AdminCell><AdminCell align="right"><Button variant="ghost" size="sm" onClick={() => setEditing(holiday)}>Edit</Button></AdminCell></AdminRow>)}</AdminTable>
    <HolidayModal record={editing === 'create' ? null : editing} open={editing !== null} onClose={() => setEditing(null)} />
  </div>;
}

function HolidayModal({ record, open, onClose }: { record: AdminHolidayResponse | null; open: boolean; onClose: () => void }) {
  const create = useCreateHoliday(); const update = useUpdateHoliday();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    const payload = { holiday_date: String(data.get('holiday_date')), name: String(data.get('name')), is_paid: data.get('paid') === 'on' };
    if (record) await update.mutateAsync({ id: record.id, body: payload }); else await create.mutateAsync(payload);
    onClose();
  }
  return <Modal title={record ? `Edit ${record.name}` : 'Add company holiday'} isOpen={open} onClose={onClose}><form className="grid gap-4" onSubmit={submit}><Input name="holiday_date" label="Date" type="date" defaultValue={record?.holiday_date} required /><Input name="name" label="Holiday name" defaultValue={record?.name} required /><Checkbox name="paid" label="Paid company holiday" defaultChecked={record?.is_paid ?? true} />{(create.isError || update.isError) && <Alert variant="error">A holiday already exists on this date or the submitted values are invalid.</Alert>}<div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="submit" isLoading={create.isPending || update.isPending}>Save holiday</Button></div></form></Modal>;
}
