import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
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
    } catch (err) {
      setError('Failed to create request. Please try again.');
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">New Request</h1>
        <Button variant="ghost" onClick={() => navigate('/app/requests')}>Cancel</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>Request Details</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            {error && <Alert variant="error">{error}</Alert>}

            <Input
              label="Request Type"
              placeholder="e.g., IT Support, HR Request"
              error={errors.request_type?.message}
              {...register('request_type', { required: 'Request type is required' })}
            />

            <Input
              label="Title"
              placeholder="Brief summary of your request"
              error={errors.title?.message}
              {...register('title', { required: 'Title is required' })}
            />

            <div className="flex flex-col gap-1.5">
              <label htmlFor="summary" className="text-sm font-medium text-gray-700">Description</label>
              <textarea
                id="summary"
                rows={4}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                placeholder="Provide details about your request..."
                {...register('summary', { required: 'Description is required' })}
              />
              {errors.summary && <p className="text-sm text-danger-600">{errors.summary.message}</p>}
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="priority" className="text-sm font-medium text-gray-700">Priority</label>
              <select
                id="priority"
                className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                {...register('priority')}
              >
                <option value="low">Low</option>
                <option value="normal">Normal</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => navigate('/app/requests')} type="button">
                Cancel
              </Button>
              <Button type="submit" isLoading={isSubmitting || createMutation.isPending}>
                Submit Request
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
