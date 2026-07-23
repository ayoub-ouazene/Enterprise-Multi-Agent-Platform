import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { useAuthContext } from '../../auth/hooks/useAuthContext';

export function AdminPage() {
  const { user } = useAuthContext();

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Administration</h1>

      <Card>
        <CardHeader>
          <CardTitle>Admin Areas</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-3">
            <li className="text-sm text-gray-600">
              Employee directory, department structure, asset inventory, software catalog, budget plans,
              leave balances, holiday calendar, staffing rules, suppliers, policy readiness, onboarding status.
            </li>
          </ul>
        </CardContent>
      </Card>

      {user && (
        <Card>
          <CardContent>
            <div className="text-sm text-gray-500">
              <p><strong>User:</strong> {user.email}</p>
              <p><strong>Role:</strong> {user.actor_type}</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
