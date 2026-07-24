import { useState } from 'react';
import { Check, X, Pencil } from 'lucide-react';
import { useAdminDepartments, useUpdateDepartment } from '../../../api/hooks/useAdmin';
import { SectionCard } from './components/SectionCard';
import { ErrorState } from './components/ErrorState';
import { TableSkeleton } from './components/TableSkeleton';
import { StatusBadge } from './components/StatusBadge';
import { useAuthContext } from '../../../auth/hooks/useAuthContext';
import { isCompanyAccount } from '../../../auth/permissions';

export function DepartmentsPage() {
  const { data: departments, isLoading, error } = useAdminDepartments();
  const update = useUpdateDepartment();
  const { user } = useAuthContext();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  const canEdit = isCompanyAccount(user);

  if (isLoading) return <TableSkeleton rows={5} />;
  if (error) return <ErrorState message="Failed to load departments." />;

  return (
    <div className="space-y-4">
      <SectionCard title="Departments" description="Company department structure">
        <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900/50">
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Name</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Type</th>
                <th className="px-4 py-2.5 text-left font-medium text-neutral-600 dark:text-neutral-400">Status</th>
                <th className="px-4 py-2.5 text-right font-medium text-neutral-600 dark:text-neutral-400">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {departments?.map((dept) => (
                <tr key={dept.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
                  <td className="px-4 py-2.5">
                    {editingId === dept.id ? (
                      <input
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="w-full rounded-md border border-neutral-300 px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-800"
                        autoFocus
                      />
                    ) : (
                      <span className="font-medium text-neutral-900 dark:text-neutral-100">{dept.name}</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400 capitalize">{dept.department_type.replace(/_/g, ' ')}</td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={dept.is_active ? 'success' : 'neutral'}>
                      {dept.is_active ? 'Active' : 'Inactive'}
                    </StatusBadge>
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    {canEdit && (
                      editingId === dept.id ? (
                        <div className="flex justify-end gap-1">
                          <button
                            onClick={() => {
                              update.mutate({ id: dept.id, body: { name: editName } }, { onSuccess: () => setEditingId(null) });
                            }}
                            disabled={!editName.trim() || update.isPending}
                            className="flex h-6 w-6 items-center justify-center rounded bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
                          >
                            <Check size={12} />
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="flex h-6 w-6 items-center justify-center rounded border border-neutral-300 text-neutral-600 dark:border-neutral-700"
                          >
                            <X size={12} />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => {
                            setEditingId(dept.id);
                            setEditName(dept.name);
                          }}
                          className="text-xs text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
                        >
                          <Pencil size={13} />
                        </button>
                      )
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  );
}
