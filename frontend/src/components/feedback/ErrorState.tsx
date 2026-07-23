import { Button } from '../ui/Button';
import { Alert } from '../ui/Alert';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = 'Something went wrong',
  message = 'There was an error loading the data. Please try again.',
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <Alert variant="error" title={title} className="mb-4 max-w-md">
        {message}
      </Alert>
      {onRetry && <Button onClick={onRetry}>Try again</Button>}
    </div>
  );
}
