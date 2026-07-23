import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Alert } from '../../components/ui/Alert';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { EmptyState } from '../../components/ui/EmptyState';
import { useOnboardingStatus, useImportJobs } from '../../api/hooks/useOnboarding';

export function OnboardingPage() {
  const { data: status, isLoading: statusLoading, error } = useOnboardingStatus();
  const { data: jobs } = useImportJobs({ limit: 10 });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Company Onboarding</h1>

      {error && (
        <Alert variant="error" title="Failed to load onboarding status">
          {error instanceof Error ? error.message : 'Please try again later.'}
        </Alert>
      )}

      {statusLoading ? <LoadingSpinner /> : status ? (
        <>
          <Card>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Activation Status</p>
                  <p className="mt-1 text-lg font-semibold">
                    {status.is_active ? 'Company is active' : 'Not yet active'}
                  </p>
                </div>
                {!status.is_active && (
                  <Button disabled={!status.can_activate}>
                    Activate Company
                  </Button>
                )}
              </div>
              {!status.onboarding_complete && status.missing_steps.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-medium text-gray-700">Missing steps:</p>
                  <ul className="mt-2 space-y-2">
                    {status.missing_steps.map((step) => (
                      <li key={step} className="flex items-center gap-2 text-sm text-gray-600">
                        <span className="flex h-4 w-4 items-center justify-center rounded-full border border-gray-300 text-[10px] font-bold text-gray-400">?</span>
                        {step}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent Import Jobs</CardTitle>
            </CardHeader>
            <CardContent>
              {!jobs || jobs.length === 0 ? (
                <EmptyState title="No import jobs yet" description="Import data to populate your company records." />
              ) : (
                <ul className="divide-y divide-gray-200">
                  {jobs.map((job) => (
                    <li key={job.id} className="py-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{job.import_type}</p>
                          <p className="text-xs text-gray-500">Status: {job.status}</p>
                        </div>
                        <span className="text-xs text-gray-400">{formatDate(job.created_at)}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}
