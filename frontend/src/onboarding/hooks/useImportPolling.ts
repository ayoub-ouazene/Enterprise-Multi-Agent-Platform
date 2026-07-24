import { useEffect, useRef, useState } from 'react';
import { useImportJob } from '../../api/hooks/useOnboarding';

const POLLING_INTERVAL_MS = 2_000;
const POLLING_STATUSES = new Set(['queued', 'processing', 'pending', 'validating']);

export function useImportPolling(jobId: string | null) {
  const { data: job, isLoading } = useImportJob(jobId ?? '', {
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      if (!query.state.data) return false;
      return POLLING_STATUSES.has(query.state.data.status) ? POLLING_INTERVAL_MS : false;
    },
  });

  const [completed, setCompleted] = useState(false);
  const prevStatusRef = useRef<string | null>(null);

  useEffect(() => {
    if (!job) return;
    const wasPolling = prevStatusRef.current ? POLLING_STATUSES.has(prevStatusRef.current) : false;
    const isPolling = POLLING_STATUSES.has(job.status);
    if (wasPolling && !isPolling) {
      setCompleted(true);
    } else if (isPolling) {
      setCompleted(false);
    }
    prevStatusRef.current = job.status;
  }, [job?.status]);

  return {
    job,
    isLoading,
    isPolling: job ? POLLING_STATUSES.has(job.status) : false,
    completed,
  };
}
