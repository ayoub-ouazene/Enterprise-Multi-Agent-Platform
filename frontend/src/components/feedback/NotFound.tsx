import { useNavigate } from 'react-router-dom';
import { FileQuestion } from 'lucide-react';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

export function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 p-4 dark:bg-neutral-900">
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="flex items-center gap-2">
            <FileQuestion size={20} className="text-neutral-500" aria-hidden="true" />
            <CardTitle>Page Not Found</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-neutral-600 dark:text-neutral-300">
            The page you are looking for does not exist or has been moved.
          </p>
          <Button onClick={() => navigate('/app')}>Go to Dashboard</Button>
        </CardContent>
      </Card>
    </div>
  );
}
