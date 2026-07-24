import { useAdminSoftwareCatalog } from '../../../api/hooks/useAdmin';
import { SectionCard } from './components/SectionCard';
import { ErrorState } from './components/ErrorState';
import { TableSkeleton } from './components/TableSkeleton';
import { StatusBadge } from './components/StatusBadge';

export function SoftwareCatalogPage() {
  const { data, isLoading, error } = useAdminSoftwareCatalog({ limit: 100 });

  if (isLoading) return <TableSkeleton rows={5} />;
  if (error) return <ErrorState message="Failed to load software catalog." />;

  return (
    <div className="space-y-4">
      <SectionCard title="Software Catalog">
        <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900/50">
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Name</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Access</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Approvals</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Licenses</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {data?.map((sw) => (
                <tr key={sw.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
                  <td className="px-4 py-2.5 font-medium text-neutral-900 dark:text-neutral-100">{sw.name}</td>
                  <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">{sw.access_type}</td>
                  <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">
                    {sw.requires_manager_approval && 'Manager '}
                    {sw.requires_it_approval && 'IT'}
                    {!sw.requires_manager_approval && !sw.requires_it_approval && 'None'}
                  </td>
                  <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">
                    {sw.license_limited ? (sw.available_license_count ?? 0) : 'Unlimited'}
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={sw.is_active ? 'success' : 'neutral'}>
                      {sw.is_active ? 'Active' : 'Inactive'}
                    </StatusBadge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data?.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-neutral-500 dark:text-neutral-400">No software entries found.</div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
