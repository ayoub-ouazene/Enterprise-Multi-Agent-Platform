import { useEffect, useState, type FormEvent } from 'react';
import { Building2 } from 'lucide-react';
import { useBeforeUnload } from 'react-router-dom';
import { useAdminCompany, useUpdateAdminCompany } from '../../../api/hooks/useAdmin';
import { AdminPageHeader } from '../../../admin/components/AdminPageHeader';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Select } from '../../../components/ui/FormControls';
import { Alert } from '../../../components/ui/Alert';
import { StatusBadge } from './components/StatusBadge';
import { ErrorState } from './components/ErrorState';
import { TableSkeleton } from './components/TableSkeleton';

const allowedCustomFields = ['timezone', 'locale', 'default_currency', 'contact_email', 'phone'] as const;

export function CompanyProfilePage() {
  const company = useAdminCompany();
  const update = useUpdateAdminCompany();
  const [editing, setEditing] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [saved, setSaved] = useState(false);
  useBeforeUnload((event) => { if (dirty) event.preventDefault(); });
  useEffect(() => { setDirty(false); setEditing(false); }, [company.data?.id]);
  if (company.isLoading) return <TableSkeleton rows={4} />;
  if (company.isError || !company.data) return <ErrorState message="Company profile could not be loaded." />;
  const record = company.data;
  const custom = record.custom_data;

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const custom_data = Object.fromEntries(allowedCustomFields.map((field) => [field, String(form.get(field) ?? '').trim()]).filter(([, value]) => value));
    await update.mutateAsync({ name: String(form.get('name')).trim(), custom_data });
    setDirty(false); setEditing(false); setSaved(true);
  }

  return <div className="space-y-6">
    <AdminPageHeader title="Company profile" description="Manage allowlisted workspace identity and regional defaults. Immutable identity and activation fields remain read-only." actions={<StatusBadge status={record.is_active ? 'success' : 'warning'}>{record.is_active ? 'Active company' : 'Setup incomplete'}</StatusBadge>} />
    {saved && <Alert variant="success">Company profile changes were confirmed by the server.</Alert>}
    {update.isError && <Alert variant="error">The profile was not changed. Review the values and retry.</Alert>}
    <form className="grid gap-5 rounded-card border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900" onSubmit={save} onChange={() => { setDirty(true); setSaved(false); }}>
      <div className="flex items-center justify-between gap-4"><div className="flex items-center gap-3"><span className="grid h-11 w-11 place-items-center rounded-xl bg-primary-50 text-primary-700 dark:bg-primary-950"><Building2 size={20} /></span><div><p className="font-semibold">{record.name}</p><p className="text-xs text-neutral-500">{record.slug}</p></div></div><Button type="button" variant="secondary" onClick={() => setEditing((value) => !value)}>{editing ? 'Cancel edit' : 'Edit profile'}</Button></div>
      <div className="grid gap-4 sm:grid-cols-2"><Input name="name" label="Display name" defaultValue={record.name} disabled={!editing} required /><Input label="Workspace slug" value={record.slug} disabled /><Input label="Company ID" value={record.id} disabled /><Input label="Activation state" value={record.is_active ? 'Active' : 'Inactive'} disabled /><Select name="timezone" label="Timezone" defaultValue={String(custom.timezone ?? 'UTC')} disabled={!editing}><option value="UTC">UTC</option><option value="Africa/Casablanca">Africa/Casablanca</option><option value="Europe/London">Europe/London</option><option value="America/New_York">America/New_York</option><option value="Asia/Dubai">Asia/Dubai</option></Select><Select name="locale" label="Locale" defaultValue={String(custom.locale ?? 'en')} disabled={!editing}><option value="en">English</option><option value="fr">French</option><option value="ar">Arabic</option></Select><Input name="default_currency" label="Default currency" defaultValue={String(custom.default_currency ?? 'USD')} minLength={3} maxLength={3} disabled={!editing} /><Input name="contact_email" type="email" label="Contact email" defaultValue={String(custom.contact_email ?? '')} disabled={!editing} /><Input name="phone" label="Contact phone" defaultValue={String(custom.phone ?? '')} disabled={!editing} /></div>
      {editing && <div className="flex justify-end"><Button type="submit" isLoading={update.isPending} disabled={!dirty}>Save profile</Button></div>}
    </form>
  </div>;
}
