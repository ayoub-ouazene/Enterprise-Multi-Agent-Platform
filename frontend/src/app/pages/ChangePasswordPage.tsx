import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { KeyRound } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Alert } from '../../components/ui/Alert';
import { useAuthContext } from '../../auth/hooks/useAuthContext';

interface ChangePasswordForm {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const { setMustChangePassword } = useAuthContext();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordForm>();

  const onSubmit = async (_data: ChangePasswordForm) => {
    setError(null);
    try {
      await new Promise((resolve) => setTimeout(resolve, 500));
      setSuccess(true);
      setMustChangePassword(false);
      setTimeout(() => navigate('/app', { replace: true }), 1500);
    } catch {
      setError('Failed to change password. Please try again.');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4 dark:bg-neutral-900">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg bg-primary-600 text-white">
            <KeyRound size={20} aria-hidden="true" />
          </div>
          <h2 className="mt-4 text-2xl font-bold text-neutral-900 dark:text-neutral-100">Change password</h2>
          <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
            You must change your password before continuing.
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          {error && <Alert variant="error">{error}</Alert>}
          {success && <Alert variant="success">Password changed successfully. Redirecting...</Alert>}

          <Input
            label="Current password"
            type="password"
            error={errors.current_password?.message}
            {...register('current_password', { required: 'Current password is required' })}
          />

          <Input
            label="New password"
            type="password"
            error={errors.new_password?.message}
            {...register('new_password', {
              required: 'New password is required',
              minLength: { value: 8, message: 'Password must be at least 8 characters' },
            })}
          />

          <Input
            label="Confirm new password"
            type="password"
            error={errors.confirm_password?.message}
            {...register('confirm_password', {
              required: 'Please confirm your password',
              validate: (value) =>
                value === watch('new_password') || 'Passwords do not match',
            })}
          />

          <Button type="submit" size="lg" className="w-full" isLoading={isSubmitting}>
            Change password
          </Button>
        </form>
      </div>
    </div>
  );
}
