import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { Check } from 'lucide-react';
import { useAuthContext } from '../../auth/hooks/useAuthContext';
import { useChangePassword } from '../../api/hooks/useAuth';
import { ApiErrorException } from '../../api/client';
import { Button } from '../../components/ui/Button';
import {
  AuthIllustration,
  AuthLayout,
  AuthPanel,
  AuthStatusMessage,
  FormErrorSummary,
  PasswordField,
} from '../../components/auth/AuthComponents';

interface ChangePasswordForm {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const { setMustChangePassword } = useAuthContext();
  const changePassword = useChangePassword();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting, submitCount },
  } = useForm<ChangePasswordForm>({ defaultValues: { current_password: '', new_password: '', confirm_password: '' } });
  const newPassword = watch('new_password');

  useEffect(() => {
    if (!success) return;
    const timer = window.setTimeout(() => navigate('/app', { replace: true }), 1200);
    return () => window.clearTimeout(timer);
  }, [navigate, success]);

  const onSubmit = async (data: ChangePasswordForm) => {
    if (changePassword.isPending || success) return;
    setError(null);
    try {
      await changePassword.mutateAsync({ current_password: data.current_password, new_password: data.new_password });
      setMustChangePassword(false);
      setSuccess(true);
    } catch (caught) {
      if (caught instanceof ApiErrorException && caught.error.status === 401) {
        setError('The current password is incorrect.');
      } else if (caught instanceof ApiErrorException) {
        setError(caught.error.message);
      } else {
        setError('The password could not be changed. Please try again.');
      }
    }
  };
  const formErrors = submitCount
    ? Object.values(errors).map((item) => item?.message).filter((item): item is string => Boolean(item))
    : [];

  return (
    <AuthLayout>
      <AuthPanel illustration={<AuthIllustration variant="password" />}>
        <div className="mx-auto max-w-md">
          <p className="text-sm font-bold uppercase tracking-[0.16em] text-primary-600 dark:text-primary-400">Required security step</p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight">Choose a private password</h1>
          <p className="mt-3 text-sm leading-6 text-neutral-600 dark:text-neutral-400">
            Your Company provisioned this account with a temporary password. Replace it before entering the application.
          </p>
          <form className="mt-8 space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
            {error && <AuthStatusMessage variant="error" title="Password not changed">{error}</AuthStatusMessage>}
            {success && <AuthStatusMessage variant="success" title="Password changed">Your workspace is ready. Redirecting securely…</AuthStatusMessage>}
            <FormErrorSummary errors={formErrors} />
            <PasswordField
              label="Current temporary password"
              autoComplete="current-password"
              disabled={success}
              error={errors.current_password?.message}
              {...register('current_password', { required: 'Current password is required' })}
            />
            <PasswordField
              label="New password"
              autoComplete="new-password"
              disabled={success}
              helperText="Use at least 12 characters. A longer unique passphrase is recommended."
              error={errors.new_password?.message}
              {...register('new_password', {
                required: 'New password is required',
                minLength: { value: 12, message: 'New password must contain at least 12 characters' },
                validate: (value) => value !== watch('current_password') || 'New password must differ from the temporary password',
              })}
            />
            <div className={`flex items-center gap-2 text-sm ${newPassword.length >= 12 ? 'text-success-700 dark:text-success-300' : 'text-neutral-500 dark:text-neutral-400'}`}>
              <Check size={16} aria-hidden="true" /> At least 12 characters
            </div>
            <PasswordField
              label="Confirm new password"
              autoComplete="new-password"
              disabled={success}
              error={errors.confirm_password?.message}
              {...register('confirm_password', {
                required: 'Confirm your new password',
                validate: (value) => value === newPassword || 'Password confirmation does not match',
              })}
            />
            <Button type="submit" size="lg" className="w-full rounded-xl" isLoading={isSubmitting || changePassword.isPending} disabled={success}>
              Update password and continue
            </Button>
          </form>
        </div>
      </AuthPanel>
    </AuthLayout>
  );
}
