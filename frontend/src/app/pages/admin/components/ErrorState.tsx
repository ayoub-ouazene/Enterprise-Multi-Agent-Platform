import { AlertCircle } from 'lucide-react';

interface ErrorStateProps {
  message?: string;
}

export function ErrorState({ message = 'Failed to load data.' }: ErrorStateProps) {
  return (
    <div className="rounded-lg border border-error-200 bg-error-50 p-4 text-sm text-error-700 dark:border-error-800 dark:bg-error-900/20 dark:text-error-300">
      <div className="flex items-center gap-2">
        <AlertCircle size={16} />
        {message}
      </div>
    </div>
  );
}
