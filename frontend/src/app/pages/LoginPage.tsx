import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Building2, Mail } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useLogin } from '../../api/hooks/useAuth';
import { api, ApiErrorException, type ApiError } from '../../api/client';
import type { AuthenticatedUser } from '../../api/types';
import { useAuthStore } from '../../auth/store';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import {
  AuthIllustration,
  AuthLayout,
  AuthPanel,
  AuthStatusMessage,
  FormErrorSummary,
  PasswordField,
} from '../../components/auth/AuthComponents';

interface LoginFormData {
  company_slug: string;
  email: string;
  password: string;
}

export function LoginPage() {
  const navigate = useNavigate();
  const loginMutation = useLogin();
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, submitCount },
  } = useForm<LoginFormData>({
    defaultValues: { company_slug: '', email: '', password: '' },
  });

  const onSubmit = async (data: LoginFormData) => {
    if (loginMutation.isPending) return;
    setError(null);
    try {
      const tokens = await loginMutation.mutateAsync(data);
      const user = await api.get<AuthenticatedUser>('/auth/me');
      const store = useAuthStore.getState();
      store.setTokens(tokens);
      store.setUser(user);
      store.setMustChangePassword(user.must_change_password);
      store.setOnboardingComplete(user.onboarding_complete);

      if (user.must_change_password) {
        navigate('/change-password', { replace: true });
      } else if (user.actor_type === 'company' && !user.company_active) {
        navigate('/app/onboarding', { replace: true });
      } else {
        navigate('/app', { replace: true });
      }
    } catch (caught) {
      const apiError = caught instanceof ApiErrorException
        ? caught.error
        : (caught as { error?: ApiError }).error;
      if (!apiError) {
        setError('An unexpected error occurred. Please try again.');
      } else if (apiError.status === 0) {
        setError('The TellUS service cannot be reached. Check your connection and try again.');
      } else if (apiError.status === 401) {
        setError('The workspace, email, or password is incorrect.');
      } else if (apiError.status === 404) {
        setError('That company workspace could not be found.');
      } else {
        setError(apiError.message);
      }
    }
  };

  const formErrors = submitCount
    ? Object.values(errors).map((item) => item?.message).filter((item): item is string => Boolean(item))
    : [];

  return (
    <AuthLayout>
      <AuthPanel illustration={<AuthIllustration variant="login" />}>
        <div className="mx-auto max-w-md">
          <p className="text-sm font-bold uppercase tracking-[0.16em] text-primary-600 dark:text-primary-400">Workspace sign in</p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight">Welcome back</h1>
          <p className="mt-3 text-sm leading-6 text-neutral-600 dark:text-neutral-400">
            Enter the workspace supplied by your Company, then use your provisioned account.
          </p>
          <form className="mt-8 space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
            {error && <AuthStatusMessage variant="error" title="Sign in failed">{error}</AuthStatusMessage>}
            <FormErrorSummary errors={formErrors} />
            <Input
              label="Company workspace"
              placeholder="your-company"
              helperText="The workspace address assigned to your organization."
              autoComplete="organization"
              icon={<Building2 size={17} aria-hidden="true" />}
              className="h-12 rounded-xl px-3 text-base"
              error={errors.company_slug?.message}
              {...register('company_slug', { required: 'Company workspace is required' })}
            />
            <Input
              label="Email address"
              type="email"
              placeholder="you@company.com"
              autoComplete="email"
              icon={<Mail size={17} aria-hidden="true" />}
              className="h-12 rounded-xl px-3 text-base"
              error={errors.email?.message}
              {...register('email', {
                required: 'Email address is required',
                pattern: { value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: 'Enter a valid email address' },
              })}
            />
            <PasswordField
              label="Password"
              autoComplete="current-password"
              error={errors.password?.message}
              {...register('password', { required: 'Password is required' })}
            />
            <p className="text-sm leading-6 text-neutral-500 dark:text-neutral-400">
              Password recovery is not yet available. Contact your Company administrator if you cannot access your account.
            </p>
            <Button className="w-full rounded-xl" size="lg" type="submit" isLoading={isSubmitting || loginMutation.isPending}>
              Sign in securely
            </Button>
          </form>
          <div className="mt-8 border-t border-neutral-200 pt-6 text-center text-sm text-neutral-600 dark:border-neutral-800 dark:text-neutral-400">
            Creating a new Company workspace?{' '}
            <Link to="/signup" className="font-semibold text-primary-600 hover:underline dark:text-primary-400">Register your Company</Link>
          </div>
        </div>
      </AuthPanel>
    </AuthLayout>
  );
}
