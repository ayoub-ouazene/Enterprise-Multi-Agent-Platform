import type { HumanActionDetail } from '../../api/types';
import { formatDateTime } from '../../lib/formatters';

export function ActionHistory({ action }: { action: HumanActionDetail }) {
  return <ol className="space-y-3" aria-label="Action history">{action.history.map((item, index) => <li key={`${item.event}-${item.occurred_at}`} className="flex gap-3"><span className={`mt-1 h-3 w-3 shrink-0 rounded-full ${index === action.history.length - 1 ? 'bg-primary-600' : 'bg-neutral-300'}`} /><div><p className="text-sm font-semibold">{item.title}</p><p className="text-sm text-neutral-600 dark:text-neutral-300">{item.description}</p><time className="text-xs text-neutral-500" dateTime={item.occurred_at}>{formatDateTime(item.occurred_at)}</time></div></li>)}</ol>;
}
