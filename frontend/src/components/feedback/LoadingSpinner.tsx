import { Spinner } from '../ui/Spinner';

export function LoadingSpinner() {
  return (
    <div className="flex min-h-[200px] items-center justify-center">
      <Spinner size="lg" />
    </div>
  );
}
