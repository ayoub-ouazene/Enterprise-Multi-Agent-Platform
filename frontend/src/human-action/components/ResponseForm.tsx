import { useRef, useState } from 'react';
import { Alert } from '../../components/ui/Alert';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import type { HumanActionDetail } from '../../api/types';
import { getActionTypeConfig } from '../registry';

export function ResponseForm({ action, onSubmit, isSubmitting }: {
  action: HumanActionDetail;
  onSubmit: (decision: string, fields: Record<string, unknown>) => void;
  isSubmitting: boolean;
}) {
  const config = getActionTypeConfig(action.action_type);
  const [decision, setDecision] = useState('');
  const [comment, setComment] = useState(() => sessionStorage.getItem(`tellus.action-comment.${action.id}`) ?? '');
  const [candidate, setCandidate] = useState('');
  const [information, setInformation] = useState<Record<string, string>>({});
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState('');
  const inFlight = useRef(false);
  const negative = ['rejected', 'failed', 'unable'].includes(decision);
  const candidates = candidateOptions(action.safe_context);
  const requestedFields = informationFields(action.safe_context);

  if (!action.can_respond || action.status !== 'pending') return <Alert variant="info" title="Read-only action">This action no longer accepts responses.</Alert>;

  const review = () => {
    if (!decision) return setError('Select an allowed response.');
    if (negative && !comment.trim()) return setError('Explain a rejection, failure, or inability to complete.');
    if (decision === 'selected' && !candidate) return setError('Select one eligible supplier.');
    if (decision === 'submitted' && requestedFields.some(field => field.required && !information[field.id]?.trim())) return setError('Complete every required information field.');
    setError('');
    setConfirming(true);
  };
  const submit = () => {
    if (inFlight.current) return;
    inFlight.current = true;
    onSubmit(decision, { notes: comment.trim(), ...(candidate ? { selected_option: candidate } : {}), ...(requestedFields.length ? { information } : {}) });
    setConfirming(false);
    window.setTimeout(() => { inFlight.current = false; }, 500);
  };

  return <div className="space-y-5">
    <fieldset><legend className="text-sm font-semibold">Choose your response</legend><div className="mt-2 grid gap-2">{action.allowed_decisions.map(item => <label key={item} className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border border-neutral-300 px-3 py-2 has-[:checked]:border-primary-600 has-[:checked]:bg-primary-50 dark:border-neutral-700 dark:has-[:checked]:bg-primary-950"><input type="radio" name="decision" value={item} checked={decision === item} onChange={() => { setDecision(item); setError(''); }} /><span className="font-medium capitalize">{item.replaceAll('_', ' ')}</span></label>)}</div></fieldset>
    {decision === 'selected' && candidates.length > 0 && <fieldset><legend className="text-sm font-semibold">Eligible supplier</legend><div className="mt-2 space-y-2">{candidates.map(item => <label key={item.id} className="flex min-h-11 items-center gap-3 rounded-lg border p-3"><input type="radio" name="candidate" value={item.id} checked={candidate === item.id} onChange={() => setCandidate(item.id)} disabled={!item.eligible} /><span>{item.label}{!item.eligible ? ' — Ineligible' : ''}</span></label>)}</div></fieldset>}
    {decision === 'submitted' && requestedFields.map(field => <label key={field.id} className="grid gap-2 text-sm font-medium">{field.label}{field.required ? ' *' : ''}<input value={information[field.id] ?? ''} onChange={event => setInformation(current => ({ ...current, [field.id]: event.target.value }))} className="h-11 rounded-lg border border-neutral-300 px-3 dark:border-neutral-700 dark:bg-neutral-950" /></label>)}
    <label className="grid gap-2 text-sm font-medium">Comment{negative ? ' (required)' : ' (optional)'}<textarea rows={4} value={comment} onChange={event => { setComment(event.target.value); sessionStorage.setItem(`tellus.action-comment.${action.id}`, event.target.value); }} className="rounded-lg border border-neutral-300 bg-white p-3 dark:border-neutral-700 dark:bg-neutral-950" /></label>
    {error && <Alert variant="error">{error}</Alert>}
    <Button onClick={review} disabled={isSubmitting}>{decision ? `${decisionLabel(decision)}…` : 'Select a response'}</Button>
    <Modal title={`Confirm ${decisionLabel(decision).toLowerCase()}`} isOpen={confirming} onClose={() => !isSubmitting && setConfirming(false)}><div className="space-y-4"><p className="text-sm">{config.consequence}</p><dl className="rounded-lg bg-neutral-50 p-4 text-sm dark:bg-neutral-800"><dt className="text-neutral-500">Selected response</dt><dd className="font-semibold capitalize">{decision.replaceAll('_', ' ')}</dd>{candidate && <><dt className="mt-2 text-neutral-500">Selected candidate</dt><dd className="font-semibold">{candidates.find(item => item.id === candidate)?.label}</dd></>}</dl>{comment && <p className="text-sm text-neutral-600">Comment: {comment}</p>}<div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => setConfirming(false)}>Go back</Button><Button onClick={submit} isLoading={isSubmitting}>Confirm {decisionLabel(decision).toLowerCase()}</Button></div></div></Modal>
  </div>;
}

function candidateOptions(context: Record<string, unknown>) {
  const value = context.candidates ?? context.shortlist;
  if (!Array.isArray(value)) return [];
  return value.flatMap((candidate, index) => candidate && typeof candidate === 'object' && !Array.isArray(candidate) ? [{
    id: String((candidate as Record<string, unknown>).id ?? index),
    label: String((candidate as Record<string, unknown>).supplier ?? (candidate as Record<string, unknown>).name ?? `Candidate ${index + 1}`),
    eligible: (candidate as Record<string, unknown>).eligible !== false,
  }] : []);
}
function informationFields(context: Record<string, unknown>) {
  if (!Array.isArray(context.requested_fields)) return [];
  return context.requested_fields.flatMap(item => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return [];
    const field = item as Record<string, unknown>;
    const id = String(field.id ?? '');
    if (!id || /password|secret|token|key/i.test(id)) return [];
    return [{ id, label: String(field.label ?? id), required: field.required === true }];
  });
}
function decisionLabel(value: string) {
  const labels: Record<string, string> = { approved: 'Approve action', rejected: 'Reject action', selected: 'Select supplier', completed: 'Confirm completion', failed: 'Report failure', unable: 'Report unable', submitted: 'Submit information', verified: 'Confirm verification' };
  return labels[value] ?? 'Confirm response';
}
