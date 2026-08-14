import { useNavigate } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

export function AccessDenied() {
  const navigate = useNavigate();

  return (
    <div className="aurora-field relative flex min-h-screen items-center justify-center bg-neutral-50 p-4 dark:bg-neutral-900">
      <Card className="glass-card relative z-10 w-full max-w-md">
        <CardHeader>
          <div className="flex flex-col items-center gap-4 text-center">
            <span
              className="feedback-float flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-rose-500 via-violet-500 to-primary-500 text-white shadow-xl shadow-rose-500/30"
              aria-hidden="true"
            >
              <ShieldAlert size={30} />
            </span>
            <div>
              <p className="mb-1 text-xs font-bold uppercase tracking-[0.2em] text-rose-500">
                Access 403
              </p>
              <CardTitle className="text-2xl">Access Denied</CardTitle>
            </div>
          </div>
        </CardHeader>
        <CardContent className="text-center">
          <p className="mb-6 text-neutral-600 dark:text-neutral-300">
            You do not have permission to access this resource. If you believe this is an error,
            please contact your administrator.
          </p>
          <div className="flex flex-col gap-3 min-[420px]:flex-row">
            <Button className="btn-sheen flex-1" onClick={() => navigate('/app')}>
              Go to Dashboard
            </Button>
            <Button className="flex-1" variant="ghost" onClick={() => navigate(-1)}>
              Go Back
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
