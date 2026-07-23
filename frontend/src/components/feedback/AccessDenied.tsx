import { useNavigate } from 'react-router-dom';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

export function AccessDenied() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="max-w-md w-full">
        <CardHeader>
          <CardTitle>Access Denied</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-gray-600">
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
