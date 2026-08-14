import { useNavigate } from 'react-router-dom';
import { FileQuestion } from 'lucide-react';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

export function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="aurora-field relative flex min-h-screen items-center justify-center bg-neutral-50 p-4 dark:bg-neutral-900">
      <Card className="glass-card relative z-10 w-full max-w-md">
        <CardHeader>
          <div className="flex flex-col items-center gap-4 text-center">
            <span
              className="feedback-float flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-500 via-violet-500 to-sky-500 text-white shadow-xl shadow-primary-500/30"
              aria-hidden="true"
            >
              <FileQuestion size={30} />
            </span>
            <div>
              <p className="mb-1 text-xs font-bold uppercase tracking-[0.2em] text-primary-500">
                Route 404
              </p>
              <CardTitle className="text-2xl">Page Not Found</CardTitle>
            </div>
          </div>
        </CardHeader>
        <CardContent className="text-center">
          <p className="mb-6 text-neutral-600 dark:text-neutral-300">
            The page you are looking for does not exist or has been moved.
          </p>
          <Button
            className="btn-sheen w-full"
            onClick={() => navigate('/app')}
          >
            Go to Dashboard
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
