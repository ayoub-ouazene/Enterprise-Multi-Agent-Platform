import { useAdminHolidays } from '../../../api/hooks/useAdmin';
import { SectionCard } from './components/SectionCard';
import { ErrorState } from './components/ErrorState';
import { TableSkeleton } from './components/TableSkeleton';
import { StatusBadge } from './components/StatusBadge';

export function HolidaysPage() {
  const { data, isLoading, error } = useAdminHolidays({ limit: 200 });

  if (isLoading) return <TableSkeleton rows={5} />;
  if (error) return <ErrorState message="Failed to load holidays." />;

  return (
    <div className="space-y-4">
      <SectionCard title="Company Holidays">
        <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900/50">
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Date</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Name</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Paid</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {data?.map((h) => (
                <tr key={h.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
                  <td className="px-4 py-2.5 font-medium text-neutral-900 dark:text-neutral-100">
                    {new Date(h.holiday_date).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">{h.name}</td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={h.is_paid ? 'success' : 'neutral'}>
                      {h.is_paid ? 'Yes' : 'No'}
                    </StatusBadge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data?.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-neutral-500 dark:text-neutral-400">No holidays found.</div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
