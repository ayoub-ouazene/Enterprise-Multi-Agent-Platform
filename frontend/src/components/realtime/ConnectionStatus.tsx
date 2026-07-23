import { clsx } from 'clsx';
import { useSseConnection } from '../../app/providers/SseProvider';

export function ConnectionStatus() {
  const { connected } = useSseConnection();

  return (
    <span
      className={clsx(
        'inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider',
        connected
          ? 'bg-success-100 text-success-700 dark:bg-success-900 dark:text-success-300'
          : 'bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400'
      )}
      role="status"
      aria-live="off"
      title={connected ? 'Realtime connection active' : 'Realtime disconnected'}
    >
      <span className={clsx('h-1.5 w-1.5 rounded-full', connected ? 'bg-success-500' : 'bg-neutral-400')} />
      {connected ? 'Live' : 'Offline'}
    </span>
  );
}
