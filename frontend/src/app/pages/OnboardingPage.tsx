import { CheckCircle2, Loader2, Rocket, XCircle } from 'lucide-react';
import { PageContainer, PageHeader, Section } from '../../components/layout/PageContainer';
import { Skeleton } from '../../components/layout/Skeleton';
import { Button } from '../../components/ui/Button';
import { Alert } from '../../components/ui/Alert';
import { EmptyState } from '../../components/ui/EmptyState';
import { useOnboardingStatus, useImportJobs } from '../../api/hooks/useOnboarding';
import { getImportJobStatusMeta } from '../../lib/status';
import { relativeTime } from '../../lib/formatters';

export function OnboardingPage() {
  const { data: status, isLoading: statusLoading, error } = useOnboardingStatus();
  const { data: jobs } = useImportJobs({ limit: 10 });

  return (
    <PageContainer>
      <PageHeader title="Company Onboarding" description="Activate your company and track import progress" />

      {error && (
        <Alert variant="error" title="Failed to load onboarding status">
          {error instanceof Error ? error.message : 'Please try again later.'}
        </Alert>
      )}

      {statusLoading ? (
        <div className="space-y-6">
          <Skeleton variant="rect" className="h-32 w-full" />
          <Skeleton variant="rect" className="h-48 w-full" />
        </div>
      ) : status ? (
        <div className="space-y-6">
          <Section>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
                    {status.is_active ? (
                      <span className="inline-flex items-center gap-1.5 text-success-700 dark:text-success-400">
                        <CheckCircle2 size={18} aria-hidden="true" />
                        Company is active
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-neutral-700 dark:text-neutral-300">
                        <XCircle size={18} aria-hidden="true" />
                        Not yet active
                      </span>
                    )}
                  </h2>
                </div>
                <div className="mt-1 flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
                  <Rocket size={14} aria-hidden="true" />
                  Onboarding {status.onboarding_complete ? 'complete' : 'in progress'}
                </div>
              </div>
              {!status.is_active && (
                <Button disabled={!status.can_activate}>
                  Activate Company
                </Button>
              )}
            </div>

            {!status.onboarding_complete && status.missing_steps.length > 0 && (
              <div className="mt-5 border-t border-neutral-200 pt-4 dark:border-neutral-700">
                <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">Missing steps</p>
                <ul className="mt-3 space-y-2">
                  {status.missing_steps.map((step) => (
                    <li key={step} className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400">
                      <span className="flex h-5 w-5 items-center justify-center rounded-full border border-neutral-300 text-[10px] font-bold text-neutral-400 dark:border-neutral-600 dark:text-neutral-500">
                        ?
                      </span>
                      {step}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Section>

          <Section title="Recent Import Jobs">
            {!jobs || jobs.length === 0 ? (
              <EmptyState title="No import jobs yet" description="Import data to populate your company records." />
            ) : (
              <div className="space-y-3">
                {jobs.map((job) => {
                  const meta = getImportJobStatusMeta(job.status);
                  return (
                    <div
                      key={job.id}
                      className="flex items-center justify-between rounded-lg border border-neutral-200 bg-white p-3 dark:border-neutral-700 dark:bg-neutral-800"
                    >
                      <div className="flex items-center gap-3">
                        <span className={`flex h-8 w-8 items-center justify-center rounded-full ${meta.category === 'success' ? 'bg-success-100 text-success-600 dark:bg-success-900 dark:text-success-300' : meta.category === 'failed' ? 'bg-danger-100 text-danger-600 dark:bg-danger-900 dark:text-danger-300' : 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-300'}`}>
                          {meta.category === 'success' ? <CheckCircle2 size={14} /> : meta.category === 'failed' ? <XCircle size={14} /> : <Loader2 size={14} className="animate-spin" />}
                        </span>
                        <div>
                          <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{job.import_type}</p>
                          <p className="text-xs text-neutral-500 dark:text-neutral-400">
                            {job.processed_count} rows • {job.status}
                          </p>
                        </div>
                      </div>
                      <span className="text-xs text-neutral-400 dark:text-neutral-500">{relativeTime(job.created_at)}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </Section>
        </div>
      ) : null}
    </PageContainer>
  );
}
