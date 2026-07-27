import { useEffect, useState } from 'react';
import { Building2, LockKeyhole } from 'lucide-react';
import type { OnboardingStatusDetailed } from '../../api/types';
import { useAdminCompany, useUpdateAdminCompany } from '../../api/hooks/useAdmin';
import { Alert } from '../../components/ui/Alert';
import { Button } from '../../components/ui/Button';
import { Skeleton } from '../../components/layout/Skeleton';

export function ProfileStep({ status }: { status: OnboardingStatusDetailed }) {
  const company = useAdminCompany();
  const update = useUpdateAdminCompany();
  const [name, setName] = useState('');
  const item = status.items.find((entry) => entry.requirement === 'company_profile');

  useEffect(() => {
    if (company.data) setName(company.data.name);
  }, [company.data]);

  const dirty = Boolean(company.data && name.trim() !== company.data.name);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (!dirty) return;
      event.preventDefault();
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);

  if (company.isLoading) return <Skeleton className="h-64" />;
  if (!company.data) return <Alert variant="error">The company profile could not be loaded.</Alert>;

  return <div className="space-y-6">
    <div className="flex items-start gap-3"><span className="grid h-11 w-11 place-items-center rounded-lg bg-primary-50 text-primary-700 dark:bg-primary-950"><Building2 /></span><div><h2 className="text-lg font-semibold">Company profile</h2><p className="text-sm text-neutral-500">Confirm the identity employees will see across the workspace.</p></div></div>
    <Alert variant={item?.satisfied ? 'success' : 'warning'} title={item?.satisfied ? 'Profile ready' : 'Profile needs attention'}>{item?.details ?? 'A display name and workspace slug are required.'}</Alert>
    <div className="grid gap-5 rounded-card border border-neutral-200 p-5 dark:border-neutral-800">
      <label className="grid gap-1.5 text-sm font-medium">Company display name<input value={name} maxLength={255} onChange={(event) => setName(event.target.value)} className="h-11 rounded-lg border border-neutral-300 px-3 dark:border-neutral-700 dark:bg-neutral-950" /><span className="text-xs font-normal text-neutral-500">Used in navigation, dashboards, and employee-facing pages.</span></label>
      <label className="grid gap-1.5 text-sm font-medium">Workspace slug<div className="flex h-11 items-center gap-2 rounded-lg border border-neutral-200 bg-neutral-50 px-3 text-neutral-600 dark:border-neutral-800 dark:bg-neutral-900"><LockKeyhole size={15} />{company.data.slug}</div><span className="text-xs font-normal text-neutral-500">The workspace identifier is immutable after registration.</span></label>
      <div className="grid gap-3 sm:grid-cols-2"><ReadOnly label="Company ID" value={company.data.id} /><ReadOnly label="Activation state" value={company.data.is_active ? 'Active' : 'Setup in progress'} /></div>
      {update.isError && <Alert variant="error">The profile was not saved. Review the value and try again.</Alert>}
      {update.isSuccess && !dirty && <Alert variant="success">Company profile saved.</Alert>}
      <div className="flex justify-end"><Button disabled={!dirty || !name.trim()} isLoading={update.isPending} onClick={() => update.mutate({ name: name.trim() })}>Save profile</Button></div>
    </div>
  </div>;
}

function ReadOnly({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs font-medium text-neutral-500">{label}</p><p className="mt-1 break-all text-sm">{value}</p></div>;
}
