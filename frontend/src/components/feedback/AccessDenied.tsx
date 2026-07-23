import { useNavigate } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

export function AccessDenied() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 p-4 dark:bg-neutral-900">
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="flex items-center gap-2">
            <ShieldAlert size={20} className="text-danger-500" aria-hidden="true" />
            <CardTitle>Access Denied</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-neutral-600 dark:text-neutral-300">
            You do not have permission to access this resource. If you believe this is an error,
            please contact your administrator.
          </p>
          <div className="flex gap-2">
            <Button onClick={() => navigate('/app')}>Go to Dashboard</Button>
            <Button variant="ghost" onClick={() => navigate(-1)}>
              Go Back
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
