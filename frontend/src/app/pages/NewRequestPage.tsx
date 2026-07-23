import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Section } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Alert } from '../../components/ui/Alert';
import { useCreateRequest } from '../../api/hooks/useRequests';

interface RequestForm {
  request_type: string;
  title: string;
  summary: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
}

export function NewRequestPage() {
  const navigate = useNavigate();
  const createMutation = useCreateRequest();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RequestForm>({
    defaultValues: { request_type: '', title: '', summary: '', priority: 'normal' },
  });

  const onSubmit = async (data: RequestForm) => {
    setError(null);
    try {
      const created = await createMutation.mutateAsync(data);
      navigate(`/app/requests/${created.id}`);
    } catch {
      setError('Failed to create request. Please try again.');
    }
  };

  return (
    <PageContainer fullWidth className="max-w-3xl">
      <div className="mb-6">
        <Button variant="ghost" onClick={() => navigate('/app/requests')}>
          <ArrowLeft size={16} className="mr-1.5" aria-hidden="true" />
          Back to requests
        </Button>
      </div>

      <PageHeader title="New Request" description="Submit a new business request" />

      <Section>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
          {error && <Alert variant="error">{error}</Alert>}

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <Input
              label="Request Type"
              placeholder="e.g., IT Support, HR Request"
              error={errors.request_type?.message}
              {...register('request_type', { required: 'Request type is required' })}
            />

            <div className="flex flex-col gap-1.5">
              <label htmlFor="priority" className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                Priority
              </label>
              <select
                id="priority"
                className="h-10 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm focus-visible:border-primary-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100"
                {...register('priority')}
              >
                <option value="low">Low</option>
                <option value="normal">Normal</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
          </div>

          <Input
            label="Title"
            placeholder="Brief summary of your request"
            error={errors.title?.message}
            {...register('title', { required: 'Title is required' })}
          />

          <div className="flex flex-col gap-1.5">
            <label htmlFor="summary" className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Description
            </label>
            <textarea
              id="summary"
              rows={4}
              className="rounded-md border border-neutral-300 px-3 py-2 text-sm focus-visible:border-primary-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100"
              placeholder="Provide details about your request..."
              {...register('summary', { required: 'Description is required' })}
            />
            {errors.summary && <p className="text-sm text-danger-600 dark:text-danger-400">{errors.summary.message}</p>}
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => navigate('/app/requests')} type="button">
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting || createMutation.isPending}>
              Submit Request
            </Button>
          </div>
        </form>
      </Section>
    </PageContainer>
  );
}
