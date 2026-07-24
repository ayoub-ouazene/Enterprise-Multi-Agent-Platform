import { useAdminAssets } from '../../../api/hooks/useAdmin';
import { SectionCard } from './components/SectionCard';
import { ErrorState } from './components/ErrorState';
import { TableSkeleton } from './components/TableSkeleton';
import { StatusBadge } from './components/StatusBadge';

export function AssetsPage() {
  const { data, isLoading, error } = useAdminAssets({ limit: 100 });

  if (isLoading) return <TableSkeleton rows={5} />;
  if (error) return <ErrorState message="Failed to load assets." />;

  return (
    <div className="space-y-4">
      <SectionCard title="Asset Inventory">
        <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900/50">
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Code</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Type</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Brand / Model</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Status</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Location</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {data?.map((asset) => (
                <tr key={asset.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
                  <td className="px-4 py-2.5 font-medium text-neutral-900 dark:text-neutral-100">{asset.asset_code}</td>
                  <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">{asset.asset_type}</td>
                  <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">{asset.brand} {asset.model}</td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={asset.status === 'available' ? 'success' : asset.status === 'assigned' ? 'info' : 'neutral'}>
                      {asset.status}
                    </StatusBadge>
                  </td>
                  <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">{asset.location || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {data?.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-neutral-500 dark:text-neutral-400">No assets found.</div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
