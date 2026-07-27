import type { ReactNode } from 'react';

export function AdminTable({
  columns,
  children,
  empty,
}: {
  columns: string[];
  children: ReactNode;
  empty?: boolean;
}) {
  return (
    <div className="overflow-x-auto rounded-card border border-neutral-200 bg-white shadow-xs dark:border-neutral-800 dark:bg-neutral-900">
      <table className="w-full min-w-[680px] text-sm">
        <thead>
          <tr className="border-b border-neutral-200 bg-neutral-50/80 dark:border-neutral-800 dark:bg-neutral-950/50">
            {columns.map((column) => <th key={column} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 last:text-right">{column}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">{children}</tbody>
      </table>
      {empty && <div className="px-4 py-12 text-center text-sm text-neutral-500">No matching records.</div>}
    </div>
  );
}

export function AdminRow({ children, onClick }: { children: ReactNode; onClick?: () => void }) {
  return <tr className="transition-colors hover:bg-neutral-50 dark:hover:bg-neutral-800/60" onClick={onClick}>{children}</tr>;
}

export function AdminCell({ children, align = 'left' }: { children: ReactNode; align?: 'left' | 'right' }) {
  return <td className={`px-4 py-3 text-neutral-700 dark:text-neutral-300 ${align === 'right' ? 'text-right' : ''}`}>{children}</td>;
}
