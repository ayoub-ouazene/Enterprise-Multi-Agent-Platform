import { useNavigate } from 'react-router-dom';
import { AlertTriangle, ArrowRight, Building2, FileWarning, Layers, Users } from 'lucide-react';
import { useAdminSummary } from '../../../api/hooks/useAdmin';
import { useDashboard } from '../../../api/hooks/useDashboard';
import { AdminPageHeader } from '../../../admin/components/AdminPageHeader';
import { Button } from '../../../components/ui/Button';
import { Alert } from '../../../components/ui/Alert';
import { MetricCard } from '../../../components/layout/MetricCard';
import { TableSkeleton } from './components/TableSkeleton';

export function AdminOverviewPage() {
  const navigate = useNavigate();
  const summary = useAdminSummary();
  const dashboard = useDashboard();
  if (summary.isLoading || dashboard.isLoading) return <TableSkeleton rows={6} />;
  if (summary.isError || dashboard.isError || !summary.data || !dashboard.data) return <Alert variant="error">Administration overview could not be loaded for this role.</Alert>;
  const attention = dashboard.data.attention.slice(0, 6);
  return <div className="space-y-6">
    <AdminPageHeader title="Administration overview" description="Company readiness, operational attention, and bounded resource previews for your authorized scope." />
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><MetricCard title="Employees" value={summary.data.total_employees} icon={<Users size={18} />} /><MetricCard title="Departments" value={summary.data.total_departments} icon={<Layers size={18} />} /><MetricCard title="Active requests" value={summary.data.active_requests} icon={<Building2 size={18} />} /><MetricCard title="Pending actions" value={summary.data.pending_human_actions} icon={<FileWarning size={18} />} /></div>
    <section className="rounded-card border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900"><div className="flex items-center justify-between gap-3"><div><h2 className="font-semibold">Attention required</h2><p className="text-sm text-neutral-500">Bounded, server-projected issues only.</p></div><span className="text-sm font-semibold">{attention.length}</span></div><div className="mt-4 grid gap-2">{attention.length === 0 ? <Alert variant="success">No immediate administration attention is reported.</Alert> : attention.map((item) => <button key={item.id} onClick={() => navigate(item.action_url)} className="flex min-h-14 items-center gap-3 rounded-lg border border-neutral-200 px-3 text-left transition-colors hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-800"><AlertTriangle size={16} className="shrink-0 text-warning-600" /><span className="min-w-0 flex-1"><strong className="block truncate text-sm">{item.title}</strong><span className="block truncate text-xs text-neutral-500">{item.explanation}</span></span><ArrowRight size={15} /></button>)}</div></section>
    <section><div className="mb-3 flex items-end justify-between"><div><h2 className="font-semibold">Department readiness</h2><p className="text-sm text-neutral-500">Member, manager, policy, and active-work summaries.</p></div><Button variant="ghost" size="sm" onClick={() => navigate('/app/admin/departments')}>All departments</Button></div><div className="grid gap-3 lg:grid-cols-2">{dashboard.data.departments.slice(0, 5).map((department) => <button key={department.id} onClick={() => navigate(`/app/admin/departments/${department.id}`)} className="rounded-card border border-neutral-200 bg-white p-4 text-left hover:border-primary-300 dark:border-neutral-800 dark:bg-neutral-900"><div className="flex items-center justify-between"><strong>{department.name}</strong><span className={`text-xs font-semibold ${department.ready ? 'text-success-700' : 'text-warning-700'}`}>{department.ready ? 'Ready' : 'Attention'}</span></div><p className="mt-2 text-sm text-neutral-500">{department.manager_label ?? 'Manager missing'} · {department.active_requests} active request(s)</p></button>)}</div></section>
  </div>;
}
