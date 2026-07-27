import { queryClient } from '../providers/QueryProvider';

export function clearSensitiveSession(logout: () => void) {
  logout();
  queryClient.clear();
}
