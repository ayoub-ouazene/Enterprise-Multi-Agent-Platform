import { Card, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Alert } from '../../components/ui/Alert';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { EmptyState } from '../../components/ui/EmptyState';
import { useHumanActions } from '../../api/hooks/useHumanActions';

export function HumanActionsPage() {
  const { data: actions, isLoading, error } = useHumanActions({ status: 'pending', limit: 50 });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Human Actions</h1>

      {error && (
        <Alert variant="error" title="Failed to load human actions">
          {error instanceof Error ? error.message : 'Please try again later.'}
        </Alert>
      )}

      <Card>
        <CardContent>
          {isLoading ? (
            <LoadingSpinner />
          ) : !actions || actions.length === 0 ? (
            <EmptyState
              title="No pending actions"
              description="All caught up. Human actions will appear here when needed."
            />
          ) : (
            <ul className="divide-y divide-gray-200">
              {actions.map((action) => (
                <li key={action.id} className="py-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-gray-900">{action.title}</p>
                        {action.status === 'pending' && (
                          <Badge variant="warning">Pending</Badge>
                        )}
                        {isOverdue(action.due_date) && (
                          <Badge variant="danger">Overdue</Badge>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-gray-600">{action.description}</p>
                      <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
                        <span>Type: {action.action_type}</span>
                        {action.due_date && (
                          <span>Due: {formatDate(action.due_date)}</span>
                        )}
                      </div>
                    </div>
                    <Button variant="primary" size="sm">Open</Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function isOverdue(dueDate: string | null): boolean {
  if (!dueDate) return false;
  return new Date(dueDate) < new Date();
}

function formatDate(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}
