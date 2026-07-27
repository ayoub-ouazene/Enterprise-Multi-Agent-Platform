import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, CheckCircle2, Info, Radio, ShieldCheck } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';
import { ActorType } from '../../api/types';
import { useCreateRequest } from '../../api/hooks/useRequests';
import { useAuthContext } from '../../auth/hooks/useAuthContext';
import { PageContainer } from '../../components/layout/PageContainer';
import { Alert } from '../../components/ui/Alert';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Select, Textarea } from '../../components/ui/FormControls';

interface RequestForm {
  request_type: string;
  title: string;
  summary: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
}

const DRAFT_KEY = 'tellus.request.draft';
const defaults: RequestForm = { request_type: '', title: '', summary: '', priority: 'normal' };

export function NewRequestPage() {
  const navigate = useNavigate();
  const { user } = useAuthContext();
  const create = useCreateRequest();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const submissionInFlight = useRef(false);
  const canSetPriority = user?.actor_type === ActorType.COMPANY || user?.actor_type === ActorType.DEPARTMENT_MANAGER;
  const form = useForm<RequestForm>({ defaultValues: readDraft() });

  useEffect(() => {
    const subscription = form.watch((value) => {
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify({ ...defaults, ...value }));
    });
    return subscription.unsubscribe;
  }, [form]);

  const submit = form.handleSubmit(async (values) => {
    if (submissionInFlight.current || create.isPending) return;
    submissionInFlight.current = true;
    setSubmitError(null);
    const payload = {
      request_type: values.request_type.trim(),
      title: values.title.trim(),
      summary: values.summary.trim(),
      ...(canSetPriority ? { priority: values.priority } : {}),
    };
    try {
      const request = await create.mutateAsync(payload);
      sessionStorage.removeItem(DRAFT_KEY);
      navigate(`/app/requests/${request.id}`, { replace: true });
    } catch {
      setSubmitError('The request was not submitted. Your draft is preserved so you can retry.');
    } finally {
      submissionInFlight.current = false;
    }
  });

  return <PageContainer className="space-y-6">
    <Link to="/app/requests" className="inline-flex min-h-10 items-center text-sm font-semibold text-neutral-600 hover:text-primary-700 dark:text-neutral-300"><ArrowLeft size={16} className="mr-2" />Back to requests</Link>
    <header><p className="text-xs font-semibold uppercase tracking-[.14em] text-primary-600">New business request</p><h1 className="mt-2 text-2xl font-bold tracking-tight text-neutral-950 sm:text-3xl dark:text-white">Describe the outcome you need</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-500">The Router will identify the owner department. You do not need to know who should handle it.</p></header>

    <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <form onSubmit={submit} className="space-y-5 rounded-card border border-neutral-200 bg-white p-5 shadow-card sm:p-7 dark:border-neutral-800 dark:bg-neutral-900" noValidate>
        {submitError && <Alert variant="error" title="Submission unsuccessful">{submitError}</Alert>}
        <Input label="Title" placeholder="A concise description of the request" autoFocus error={form.formState.errors.title?.message} aria-invalid={Boolean(form.formState.errors.title)} {...form.register('title', { required: 'Enter a request title.', minLength: { value: 3, message: 'Use at least 3 characters.' }, maxLength: { value: 255, message: 'Use 255 characters or fewer.' } })} />
        <Input label="Request type" placeholder="For example: software access, leave, hardware, supplier search" error={form.formState.errors.request_type?.message} aria-invalid={Boolean(form.formState.errors.request_type)} {...form.register('request_type', { required: 'Enter a request type.', maxLength: { value: 100, message: 'Use 100 characters or fewer.' } })} />
        <div><Textarea label="Detailed description" rows={9} placeholder="Describe the goal, relevant context, constraints, and the result you expect." aria-invalid={Boolean(form.formState.errors.summary)} {...form.register('summary', { required: 'Describe what you need.', minLength: { value: 10, message: 'Add enough context to help route the request.' }, maxLength: { value: 10_000, message: 'Use 10,000 characters or fewer.' } })} />{form.formState.errors.summary && <p className="mt-1.5 text-sm text-danger-600" role="alert">{form.formState.errors.summary.message}</p>}</div>
        {canSetPriority && <Select label="Priority" {...form.register('priority')}><option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option><option value="urgent">Urgent</option></Select>}
        <div className="flex flex-col-reverse gap-3 border-t border-neutral-100 pt-5 sm:flex-row sm:justify-end dark:border-neutral-800"><Button type="button" variant="secondary" onClick={() => navigate('/app/requests')}>Cancel</Button><Button type="submit" isLoading={form.formState.isSubmitting || create.isPending}>Submit request</Button></div>
      </form>

      <aside className="rounded-card border border-primary-100 bg-primary-50/60 p-5 dark:border-primary-900 dark:bg-primary-950/30" aria-labelledby="request-guidance"><h2 id="request-guidance" className="font-semibold text-neutral-950 dark:text-white">What happens next</h2><ul className="mt-4 space-y-4"><Guidance icon={<Info size={17} />} title="Describe the goal" text="Include useful context without choosing a department or workflow stage." /><Guidance icon={<Radio size={17} />} title="Routing and clarification" text="The system may ask up to three focused clarification questions." /><Guidance icon={<ShieldCheck size={17} />} title="Authorized human help" text="Approvals or manual work appear as explicit HumanActions when required." /><Guidance icon={<CheckCircle2 size={17} />} title="Live, honest progress" text="The detail page updates from authoritative workflow state after submission." /></ul></aside>
    </div>
  </PageContainer>;
}

function Guidance({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return <li className="flex gap-3"><span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white text-primary-600 shadow-xs dark:bg-neutral-900">{icon}</span><div><p className="text-sm font-semibold text-neutral-900 dark:text-white">{title}</p><p className="mt-1 text-xs leading-5 text-neutral-600 dark:text-neutral-400">{text}</p></div></li>;
}

function readDraft(): RequestForm {
  try {
    const raw = sessionStorage.getItem(DRAFT_KEY);
    return raw ? { ...defaults, ...JSON.parse(raw) } : defaults;
  } catch {
    sessionStorage.removeItem(DRAFT_KEY);
    return defaults;
  }
}
