import { ReactNode } from 'react';
import { clsx } from 'clsx';

interface Column<T> {
  header: string;
  accessor: (row: T) => ReactNode;
  className?: string;
  headerClassName?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (row: T) => string;
  emptyMessage?: string;
  className?: string;
  rowClassName?: string;
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  emptyMessage = 'No data available.',
  className,
  rowClassName,
}: DataTableProps<T>) {
  return (
    <div className={clsx('overflow-x-auto rounded-xl border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-800', className)}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900/50">
            {columns.map((col, i) => (
              <th
                key={i}
                className={clsx(
                  'px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400',
                  col.headerClassName
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
          {data.map((row) => (
            <tr
              key={keyExtractor(row)}
              className={clsx('hover:bg-neutral-50 dark:hover:bg-neutral-900/50 transition-colors', rowClassName)}
            >
              {columns.map((col, i) => (
                <td key={i} className={clsx('px-4 py-2.5', col.className)}>
                  {col.accessor(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length === 0 && (
        <div className="px-4 py-8 text-center text-sm text-neutral-500 dark:text-neutral-400">
          {emptyMessage}
        </div>
      )}
    </div>
  );
}
