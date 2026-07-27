import { clsx } from 'clsx';

export function Tabs({ items, value, onChange, label = 'Sections' }: { items: { value: string; label: string; count?: number }[]; value: string; onChange: (value: string) => void; label?: string }) {
  return <div role="tablist" aria-label={label} className="flex gap-1 overflow-x-auto border-b border-neutral-200 dark:border-neutral-800">{items.map((item) => <button key={item.value} role="tab" aria-selected={value === item.value} onClick={() => onChange(item.value)} className={clsx('relative min-h-11 whitespace-nowrap px-3 text-sm font-medium transition-colors', value === item.value ? 'text-primary-700 after:absolute after:inset-x-2 after:bottom-0 after:h-0.5 after:bg-primary-600 dark:text-primary-300' : 'text-neutral-500 hover:text-neutral-900 dark:hover:text-white')}>{item.label}{item.count !== undefined && <span className="ml-1.5 rounded-full bg-neutral-100 px-1.5 py-0.5 text-[10px] dark:bg-neutral-800">{item.count}</span>}</button>)}</div>;
}
