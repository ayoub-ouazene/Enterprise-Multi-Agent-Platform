import { forwardRef, useId, type InputHTMLAttributes, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';
import { clsx } from 'clsx';

const control = 'w-full rounded-lg border border-neutral-300 bg-white px-3 text-sm text-neutral-900 shadow-xs transition-colors placeholder:text-neutral-400 focus:border-primary-500 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white';

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement> & { label?: string }>(
  function Select({ label, id, className, children, ...props }, ref) {
    const generated = useId();
    const controlId = id ?? generated;
    return <label className="grid gap-1.5 text-sm font-medium text-neutral-700 dark:text-neutral-300">{label}<select ref={ref} id={controlId} className={clsx(control, 'h-10', className)} {...props}>{children}</select></label>;
  },
);

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string }>(
  function Textarea({ label, id, className, ...props }, ref) {
    const generated = useId();
    const controlId = id ?? generated;
    return <label className="grid gap-1.5 text-sm font-medium text-neutral-700 dark:text-neutral-300">{label}<textarea ref={ref} id={controlId} className={clsx(control, 'min-h-24 py-2', className)} {...props} /></label>;
  },
);

export const Checkbox = forwardRef<HTMLInputElement, Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & { label: string }>(
  function Checkbox({ label, className, ...props }, ref) {
    return <label className="inline-flex min-h-10 cursor-pointer items-center gap-2.5 text-sm text-neutral-700 dark:text-neutral-300"><input ref={ref} type="checkbox" className={clsx('h-4 w-4 rounded border-neutral-300 text-primary-600 focus:ring-primary-500 dark:border-neutral-600 dark:bg-neutral-900', className)} {...props} /><span>{label}</span></label>;
  },
);

export function RadioGroup({ legend, name, options, value, onChange }: { legend: string; name: string; options: { label: string; value: string }[]; value?: string; onChange?: (value: string) => void }) {
  return <fieldset><legend className="mb-2 text-sm font-medium text-neutral-700 dark:text-neutral-300">{legend}</legend><div className="grid gap-2">{options.map((option) => <label key={option.value} className="inline-flex min-h-10 cursor-pointer items-center gap-2.5 text-sm"><input type="radio" name={name} value={option.value} checked={value === option.value} onChange={() => onChange?.(option.value)} className="h-4 w-4 text-primary-600 focus:ring-primary-500" />{option.label}</label>)}</div></fieldset>;
}

export function Switch({ checked, onChange, label, disabled }: { checked: boolean; onChange: (checked: boolean) => void; label: string; disabled?: boolean }) {
  return <label className="inline-flex min-h-10 cursor-pointer items-center gap-3"><button type="button" role="switch" aria-checked={checked} disabled={disabled} onClick={() => onChange(!checked)} className={clsx('relative h-6 w-11 rounded-full transition-colors duration-ui disabled:opacity-50', checked ? 'bg-primary-600' : 'bg-neutral-300 dark:bg-neutral-700')}><span className={clsx('absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-ui', checked && 'translate-x-5')} /></button><span className="text-sm text-neutral-700 dark:text-neutral-300">{label}</span></label>;
}
