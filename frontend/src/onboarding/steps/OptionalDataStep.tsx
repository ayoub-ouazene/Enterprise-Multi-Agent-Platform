import { Database, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Alert } from '../../components/ui/Alert';

const modules = [
  ['IT assets', 'Track approved equipment, status, assignees, and locations.', '/app/admin/assets'],
  ['Software catalogue', 'Configure software access and available licences.', '/app/admin/software'],
  ['Finance budgets', 'Create decimal-safe budgets and approval thresholds.', '/app/admin/budgets'],
  ['Supplier catalogue', 'Maintain eligible suppliers and compliance state.', '/app/admin/suppliers'],
  ['Company holidays', 'Configure the authoritative workday calendar.', '/app/admin/holidays'],
  ['Staffing rules', 'Set minimum staffing requirements by department.', '/app/admin/staffing-rules'],
] as const;

export function OptionalDataStep() {
  return <div className="space-y-6">
    <div className="flex items-start gap-3"><span className="grid h-11 w-11 place-items-center rounded-lg bg-primary-50 text-primary-700 dark:bg-primary-950"><Database /></span><div><h2 className="text-lg font-semibold">Optional operational data</h2><p className="text-sm text-neutral-500">Improve workflow coverage now or configure these modules after activation.</p></div></div>
    <Alert variant="info" title="These modules do not currently block activation">The backend checklist remains authoritative. Import controls are shown only when a module has a supported controlled-import endpoint.</Alert>
    <div className="grid gap-3 sm:grid-cols-2">{modules.map(([title, description, href]) => <article key={title} className="rounded-card border border-neutral-200 p-4 dark:border-neutral-800"><h3 className="font-semibold">{title}</h3><p className="mt-1 min-h-10 text-sm text-neutral-500">{description}</p><div className="mt-3 flex items-center justify-between"><span className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Optional · manage later</span><Link to={href} className="inline-flex min-h-10 items-center gap-1 text-sm font-semibold text-primary-700">Open after activation <ExternalLink size={14} /></Link></div></article>)}</div>
  </div>;
}
