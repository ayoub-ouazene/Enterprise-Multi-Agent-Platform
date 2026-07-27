import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { getActionTypeConfig } from '../registry';

export function DecisionPackageView({ actionType, context }: { actionType: string; context: Record<string, unknown> }) {
  const config = getActionTypeConfig(actionType);
  const entries = config.safeFields.flatMap((key) => key in context ? [[key, context[key]] as const] : []);
  if (!entries.length) return <p className="text-sm text-neutral-500">No additional authorized context was provided.</p>;
  return <div className="space-y-3">{entries.map(([key, value]) => key === 'candidates' || key === 'shortlist'
    ? <CandidateComparison key={key} value={value} />
    : <SafeFact key={key} label={label(key)} value={value} />)}</div>;
}

function CandidateComparison({ value }: { value: unknown }) {
  if (!Array.isArray(value)) return null;
  return <section aria-labelledby="candidate-heading"><h3 id="candidate-heading" className="mb-2 text-sm font-semibold">Validated candidates</h3><div className="grid gap-3">{value.map((candidate, index) => {
    if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate)) return null;
    const item = candidate as Record<string, unknown>;
    const eligible = item.eligible !== false;
    return <article key={String(item.id ?? index)} className="rounded-card border border-neutral-200 p-4 dark:border-neutral-700"><div className="flex items-start justify-between gap-3"><p className="font-semibold">{String(item.supplier ?? item.name ?? `Candidate ${index + 1}`)}</p><span className={`inline-flex items-center gap-1 text-xs font-semibold ${eligible ? 'text-success-700' : 'text-danger-700'}`}>{eligible ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}{eligible ? 'Eligible' : 'Ineligible'}</span></div><dl className="mt-3 grid grid-cols-2 gap-2 text-sm">{['rank','score','total_cost','currency','availability','finance_validation'].map(key => key in item ? <div key={key}><dt className="text-xs text-neutral-500">{label(key)}</dt><dd>{String(item[key])}</dd></div> : null)}</dl>{!eligible && item.reason ? <p className="mt-2 text-sm text-danger-700">{String(item.reason)}</p> : null}</article>;
  })}</div></section>;
}

function SafeFact({ label: title, value }: { label: string; value: unknown }) {
  if (value === null || value === undefined) return null;
  const display = Array.isArray(value)
    ? value.filter(item => ['string','number','boolean'].includes(typeof item)).map(String).join(', ')
    : typeof value === 'object' ? null : String(value);
  if (!display) return null;
  return <div className="rounded-card border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900"><p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</p><p className="mt-1 whitespace-pre-wrap text-sm text-neutral-900 dark:text-neutral-100">{display}</p></div>;
}

function label(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, character => character.toUpperCase());
}
