import { useNavigate } from 'react-router-dom';
import { FileUp, ShieldCheck } from 'lucide-react';
import { useAdminDepartments, useAdminPolicyReadiness } from '../../../api/hooks/useAdmin';
import { AdminPageHeader } from '../../../admin/components/AdminPageHeader';
import { Button } from '../../../components/ui/Button';
import { Alert } from '../../../components/ui/Alert';
import { StatusBadge } from './components/StatusBadge';
import { TableSkeleton } from './components/TableSkeleton';

export function PoliciesPage() {
  const navigate = useNavigate();
  const readiness = useAdminPolicyReadiness();
  const departments = useAdminDepartments();
  if (readiness.isLoading) return <TableSkeleton rows={5} />;
  return <div className="space-y-6">
    <AdminPageHeader title="Policy readiness" description="Review active policy coverage without exposing extracted text, embeddings, namespaces, or vector metadata." actions={<Button onClick={() => navigate('/app/admin/documents')}><FileUp size={16} className="mr-2" />Manage documents</Button>} />
    {readiness.isError && <Alert variant="error">Policy readiness could not be loaded.</Alert>}
    {readiness.data && <Alert variant={readiness.data.ready ? 'success' : 'warning'} title={readiness.data.ready ? 'Policy coverage ready' : 'Policy coverage needs attention'}>{readiness.data.ingested_active_policies} active ingested policy document(s). Only enabled departments block operational readiness.</Alert>}
    <div className="grid gap-4 lg:grid-cols-2">{departments.data?.map((department) => {
      const covered = readiness.data?.department_coverage[department.department_type] ?? false;
      return <article key={department.id} className="rounded-card border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900"><div className="flex items-start justify-between gap-3"><div className="flex gap-3"><span className="grid h-10 w-10 place-items-center rounded-lg bg-neutral-100 dark:bg-neutral-800"><ShieldCheck size={18} /></span><div><h2 className="font-semibold">{department.name}</h2><p className="text-sm text-neutral-500">{department.is_active ? 'Enabled department' : 'Department disabled'}</p></div></div><StatusBadge status={covered ? 'success' : department.is_active ? 'warning' : 'neutral'}>{covered ? 'Covered' : department.is_active ? 'Missing' : 'Not blocking'}</StatusBadge></div>{department.is_active && !covered && <Button variant="secondary" size="sm" className="mt-4" onClick={() => navigate('/app/admin/documents')}>Upload policy</Button>}</article>;
    })}</div>
  </div>;
}
