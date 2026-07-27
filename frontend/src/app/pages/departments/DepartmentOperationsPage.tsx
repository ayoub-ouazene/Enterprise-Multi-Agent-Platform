import { ArrowRight, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useDepartmentOperationalRecords } from '../../../api/hooks/useDepartments';
import type { DepartmentOperationalRecord } from '../../../api/types';
import { getDepartmentMeta, slugToDepartmentType } from '../../../lib/departments';
import { relativeTime } from '../../../lib/formatters';
import { PageContainer, PageHeader } from '../../../components/layout/PageContainer';
import { Input } from '../../../components/ui/Input';
import { Tabs } from '../../../components/ui/Tabs';
import { Button } from '../../../components/ui/Button';
import { EmptyState } from '../../../components/ui/EmptyState';
import { Alert } from '../../../components/ui/Alert';
import { StatusBadge } from '../admin/components/StatusBadge';
import { TableSkeleton } from '../admin/components/TableSkeleton';

export function DepartmentOperationsPage() {
  const { deptSlug } = useParams<{ deptSlug: string }>();
  const departmentType = deptSlug ? slugToDepartmentType(deptSlug) : undefined;
  const meta = departmentType ? getDepartmentMeta(departmentType) : undefined;
  const [sectionId, setSectionId] = useState(meta?.sections[0]?.id ?? '');
  const [query, setQuery] = useState('');
  const records = useDepartmentOperationalRecords(departmentType ?? '', { limit: 100 });

  const sectionIdFromMeta = meta ? (meta.sections.find((item) => item.id === sectionId) ?? meta.sections[0])?.id ?? '' : '';
  const section = meta ? (meta.sections.find((item) => item.id === sectionIdFromMeta) ?? meta.sections[0]) : undefined;
  if (!section) return <PageContainer><Alert variant="error">Section not found.</Alert></PageContainer>;
  const visible = useMemo(
    () => (records.data ?? []).filter((record) => (
      (section?.recordTypes ?? []).includes(record.record_type)
      && (!query.trim() || `${record.title} ${record.summary ?? ''} ${record.status}`.toLowerCase().includes(query.toLowerCase()))
    )),
    [query, records.data, section],
  );

  if (!departmentType || !meta) return <PageContainer><Alert variant="error">Unknown department workspace.</Alert></PageContainer>;

  return (
    <PageContainer>
      <PageHeader title="Operations" description={`Authoritative ${meta.label} extension records. Workflow execution remains in the existing request runtime.`} />
      <Tabs
        items={meta.sections.map((item) => ({ value: item.id, label: item.label }))}
        value={section.id}
        onChange={setSectionId}
        label={`${meta.label} operational sections`}
      />
      <div className="mt-4 max-w-md">
        <Input label={`Search ${section.label.toLowerCase()}`} value={query} onChange={(event) => setQuery(event.target.value)} icon={<Search size={16} />} />
      </div>
      <div className="mt-5">
        {records.isLoading && <TableSkeleton rows={5} />}
        {records.isError && <Alert variant="error">This operational section could not be loaded. Other workspace sections remain available.</Alert>}
        {!records.isLoading && !records.isError && visible.length === 0 && (
          <EmptyState title={section.emptyTitle} description={section.emptyDescription} />
        )}
        <div className="grid gap-4 xl:grid-cols-2">
          {visible.map((record) => <OperationalRecordCard key={`${record.record_type}-${record.id}`} record={record} />)}
        </div>
      </div>
    </PageContainer>
  );
}

export function OperationalRecordCard({ record }: { record: DepartmentOperationalRecord }) {
  const navigate = useNavigate();
  return (
    <article className="rounded-card border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-400">{record.record_type.replaceAll('_', ' ')}</p>
          <h2 className="mt-1 truncate font-semibold">{record.title}</h2>
          {record.summary && <p className="mt-1 line-clamp-2 text-sm text-neutral-500">{record.summary}</p>}
        </div>
        <StatusBadge status={statusTone(record.status)}>{record.status.replaceAll('_', ' ')}</StatusBadge>
      </div>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2">
        {record.fields.map((field) => (
          <div key={field.label} className="rounded-lg bg-neutral-50 px-3 py-2 dark:bg-neutral-800">
            <dt className="text-[11px] font-medium text-neutral-500">{field.label}</dt>
            <dd className={`mt-1 break-words text-sm font-semibold ${fieldTone(field.emphasis)}`}>{field.value}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-4 flex items-center justify-between gap-3">
        <span className="text-xs text-neutral-400">{record.updated_at ? `Updated ${relativeTime(record.updated_at)}` : 'Authoritative record'}</span>
        {record.action_url && <Button variant="ghost" size="sm" onClick={() => navigate(record.action_url!)}>Open request <ArrowRight size={14} className="ml-1" /></Button>}
      </div>
    </article>
  );
}

function statusTone(status: string): 'success' | 'warning' | 'error' | 'info' | 'neutral' {
  if (['completed', 'resolved', 'approved', 'eligible', 'confirmed', 'selected'].includes(status)) return 'success';
  if (['failed', 'rejected', 'blocked', 'denied', 'critical'].includes(status)) return 'error';
  if (status.includes('waiting') || status.includes('pending') || status.includes('required')) return 'warning';
  return 'info';
}

function fieldTone(emphasis: string) {
  if (emphasis === 'positive') return 'text-success-700 dark:text-success-300';
  if (emphasis === 'warning') return 'text-warning-700 dark:text-warning-300';
  if (emphasis === 'critical') return 'text-error-700 dark:text-error-300';
  return 'text-neutral-800 dark:text-neutral-100';
}
