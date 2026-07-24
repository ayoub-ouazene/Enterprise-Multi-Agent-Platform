import { useState } from 'react';
import { Building2, Check, X, Pencil } from 'lucide-react';
import { useAdminCompany, useUpdateAdminCompany } from '../../../api/hooks/useAdmin';
import { SectionCard } from './components/SectionCard';
import { ErrorState } from './components/ErrorState';
import { TableSkeleton } from './components/TableSkeleton';

export function CompanyProfilePage() {
  const { data: company, isLoading, error } = useAdminCompany();
  const update = useUpdateAdminCompany();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState('');

  if (isLoading) return <TableSkeleton rows={3} />;
  if (error || !company) return <ErrorState message="Failed to load company profile." />;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <SectionCard title="Company Profile" description="View and manage company details">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100 text-primary-600 dark:bg-primary-900/30">
                <Building2 size={20} />
              </div>
              <div>
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{company.name}</p>
                <p className="text-xs text-neutral-500 dark:text-neutral-400">Slug: {company.slug}</p>
              </div>
            </div>
            {!editing && (
              <button
                onClick={() => {
                  setName(company.name);
                  setEditing(true);
                }}
                className="flex items-center gap-1 rounded-md border border-neutral-300 px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
              >
                <Pencil size={12} />
                Edit Name
              </button>
            )}
          </div>

          {editing && (
            <div className="flex items-center gap-2">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="flex-1 rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
                placeholder="Company name"
              />
              <button
                onClick={() => {
                  update.mutate({ name }, { onSuccess: () => setEditing(false) });
                }}
                disabled={!name.trim() || update.isPending}
                className="flex h-9 w-9 items-center justify-center rounded-md bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
              >
                <Check size={16} />
              </button>
              <button
                onClick={() => setEditing(false)}
                className="flex h-9 w-9 items-center justify-center rounded-md border border-neutral-300 text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-400"
              >
                <X size={16} />
              </button>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Status</p>
              <p className="mt-0.5 font-medium text-neutral-900 dark:text-neutral-100">
                {company.is_active ? 'Active' : 'Inactive'}
              </p>
            </div>
            <div>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Created</p>
              <p className="mt-0.5 font-medium text-neutral-900 dark:text-neutral-100">
                {new Date(company.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>
      </SectionCard>
    </div>
  );
}
