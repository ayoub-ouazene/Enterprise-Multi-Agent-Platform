import { useEffect, useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';

export function ActivationModal({ open, onClose, onConfirm, isActivating }: { open: boolean; onClose: () => void; onConfirm: () => void; isActivating: boolean }) {
  const [confirmed, setConfirmed] = useState(false);
  useEffect(() => { if (!open) setConfirmed(false); }, [open]);
  return <Modal title="Activate Company workspace" isOpen={open} onClose={() => !isActivating && onClose()}>
    <div className="space-y-4">
      <div className="flex gap-3 rounded-lg bg-warning-50 p-4 text-sm text-warning-900 dark:bg-warning-950 dark:text-warning-100"><ShieldCheck className="shrink-0" size={19} /><p>Activation makes enabled departments operational and allows provisioned users to sign in according to their account state. Missing optional data may limit some workflows.</p></div>
      <label className="flex min-h-11 items-start gap-3 rounded-lg border border-neutral-200 p-3 dark:border-neutral-700"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} className="mt-1" /><span><strong className="block text-sm">I reviewed the authoritative readiness checklist</strong><span className="text-sm text-neutral-500">The backend will revalidate every required condition before activation.</span></span></label>
      <div className="flex justify-end gap-2"><Button variant="secondary" onClick={onClose} disabled={isActivating}>Go back</Button><Button onClick={onConfirm} disabled={!confirmed} isLoading={isActivating}>Activate Company</Button></div>
    </div>
  </Modal>;
}
