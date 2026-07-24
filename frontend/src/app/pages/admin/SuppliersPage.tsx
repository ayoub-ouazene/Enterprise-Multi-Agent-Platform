import { useAdminSuppliers } from '../../../api/hooks/useAdmin';
import { SectionCard } from './components/SectionCard';
import { ErrorState } from './components/ErrorState';
import { TableSkeleton } from './components/TableSkeleton';
import { StatusBadge } from './components/StatusBadge';

export function SuppliersPage() {
  const { data, isLoading, error } = useAdminSuppliers({ limit: 100 });

  if (isLoading) return <TableSkeleton rows={5} />;
  if (error) return <ErrorState message="Failed to load suppliers." />;

  return (
    <div className="space-y-4">
      <SectionCard title="Suppliers">
        <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900/50">
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Name</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Contact</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Email</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Phone</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {data?.map((s) => (
                <tr key={s.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
                  <td className="px-4 py-2.5 font-medium text-neutral-900 dark:text-neutral-100">{s.name}</td>
                  <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">{s.contact_person || '—'}</td>
                  <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">{s.email || '—'}</td>
                  <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">{s.phone || '—'}</td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={s.is_active ? 'success' : 'neutral'}>
                      {s.is_active ? 'Active' : 'Inactive'}
                    </StatusBadge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data?.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-neutral-500 dark:text-neutral-400">No suppliers found.</div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
