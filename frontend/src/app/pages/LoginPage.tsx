import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { Building2 } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Alert } from '../../components/ui/Alert';
import { useLogin } from '../../api/hooks/useAuth';
import { useAuthStore } from '../../auth/store';
import type { ApiError } from '../../api/client';

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
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    defaultValues: { company_slug: '', email: '', password: '' },
  });

  const onSubmit = async (data: LoginFormData) => {
    setError(null);
    try {
      const response = await loginMutation.mutateAsync(data);
      useAuthStore.getState().setTokens(response);

      const user = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'}/auth/me`, {
        headers: { Authorization: `Bearer ${response.access_token}` },
      }).then((r) => r.json());

      useAuthStore.getState().setUser(user);

      if (user.must_change_password) {
        useAuthStore.getState().setMustChangePassword(true);
        navigate('/change-password', { replace: true });
        return;
      }

      if (user.actor_type === 'company' && user.onboarding_complete === false) {
        useAuthStore.getState().setOnboardingComplete(false);
        navigate('/app/onboarding', { replace: true });
        return;
      }

      navigate('/app', { replace: true });
    } catch (err) {
      const apiErr = (err as { error?: ApiError }).error;
      if (apiErr) {
        setError(apiErr.message);
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4 py-12 dark:bg-neutral-900">
      <div className="w-full max-w-sm space-y-8">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-primary-600 text-white text-xl font-bold">
            EM
          </div>
          <h2 className="mt-6 text-2xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
            Sign in to your account
          </h2>
          <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
            Enterprise Multi-Agent Platform
          </p>
        </div>

        <form className="mt-8 space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
          {error && (
            <Alert variant="error" title="Sign in failed">
              {error}
            </Alert>
          )}

          <div className="space-y-4">
            <Input
              label="Workspace"
              placeholder="your-company"
              helperText="Your company workspace slug"
              error={errors.company_slug?.message}
              autoComplete="organization"
              icon={<Building2 size={16} className="text-neutral-400" aria-hidden="true" />}
              {...register('company_slug', { required: 'Workspace is required' })}
            />

            <Input
              label="Email address"
              type="email"
              placeholder="you@example.com"
              error={errors.email?.message}
              autoComplete="email"
              {...register('email', {
                required: 'Email is required',
                pattern: {
                  value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                  message: 'Please enter a valid email',
                },
              })}
            />

            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              error={errors.password?.message}
              autoComplete="current-password"
              {...register('password', {
                required: 'Password is required',
                minLength: {
                  value: 6,
                  message: 'Password must be at least 6 characters',
                },
              })}
            />
          </div>

          <Button
            type="submit"
            size="lg"
            className="w-full"
            isLoading={isSubmitting || loginMutation.isPending}
          >
            Sign in
          </Button>
        </form>
      </div>
    </div>
  );
}
