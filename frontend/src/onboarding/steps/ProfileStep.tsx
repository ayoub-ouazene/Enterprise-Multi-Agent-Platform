import { Building2, Info } from 'lucide-react';
import type { OnboardingStatusDetailed } from '../../api/types';
import { useAdminDepartments } from '../../api/hooks/useOnboarding';
import { Alert } from '../../components/ui/Alert';
import { Skeleton } from '../../components/layout/Skeleton';

interface ProfileStepProps {
  status: OnboardingStatusDetailed;
}

export function ProfileStep({ status }: ProfileStepProps) {
  const { data: departments, isLoading } = useAdminDepartments();
  const profileItem = status.items.find((i) => i.requirement === 'company_profile');
  const companyName = departments?.[0]?.name?.split(' ')[0] ?? 'Your Company';

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-300">
          <Building2 size={20} />
        </div>
        <div>
          <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">Company Profile</h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">Basic company identity</p>
        </div>
      </div>

      {profileItem?.satisfied ? (
        <Alert variant="success" title="Profile complete">
          Your company profile is set up and ready.
        </Alert>
      ) : (
        <Alert variant="warning" title="Profile incomplete">
          {profileItem?.details ?? 'Company name and slug are required.'}
        </Alert>
      )}

      {isLoading ? (
        <Skeleton variant="rect" className="h-20 w-full" />
      ) : (
        <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-800">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-medium text-neutral-500 dark:text-neutral-400">Company Name</label>
              <p className="mt-1 text-sm font-medium text-neutral-900 dark:text-neutral-100">{companyName}</p>
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-500 dark:text-neutral-400">Slug</label>
              <p className="mt-1 text-sm font-medium text-neutral-900 dark:text-neutral-100">{companyName.toLowerCase().replace(/\s+/g, '-')}</p>
            </div>
          </div>
          <div className="mt-3 flex items-start gap-2 rounded-md bg-info-50 p-2 text-xs text-info-800 dark:bg-info-900/30 dark:text-info-200">
            <Info size={14} className="mt-0.5 shrink-0" />
            <p>
              Company name and slug were set during registration and cannot be changed here.
              Contact support to update these fields.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
