import { useNavigate } from 'react-router-dom';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

export function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="max-w-md w-full">
        <CardHeader>
          <CardTitle>Page Not Found</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-gray-600">
            The page you are looking for does not exist or has been moved.
          </p>
          <Button onClick={() => navigate('/app')}>Go to Dashboard</Button>
        </CardContent>
      </Card>
    </div>
  );
}
