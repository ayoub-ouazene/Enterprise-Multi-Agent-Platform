import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Building2, Check, Mail } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useRegisterCompany } from '../../api/hooks/useAuth';
import { api, ApiErrorException } from '../../api/client';
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

interface SignupForm {
  company_name: string;
  company_slug: string;
  email: string;
  password: string;
  confirm_password: string;
}

function slugify(value: string) {
  return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100);
}

export function SignupPage() {
  const navigate = useNavigate();
  const registration = useRegisterCompany();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting, submitCount, dirtyFields },
  } = useForm<SignupForm>({ defaultValues: { company_name: '', company_slug: '', email: '', password: '', confirm_password: '' } });
  const companyName = watch('company_name');
  const password = watch('password');

  useEffect(() => {
    if (!dirtyFields.company_slug) {
      setValue('company_slug', slugify(companyName), { shouldValidate: false });
    }
  }, [companyName, dirtyFields.company_slug, setValue]);

  async function onSubmit(form: SignupForm) {
    if (registration.isPending) return;
    setServerError(null);
    try {
      const tokens = await registration.mutateAsync({
        company_name: form.company_name.trim(),
        company_slug: form.company_slug.trim(),
        email: form.email.trim(),
        password: form.password,
      });
      const user = await api.get<AuthenticatedUser>('/auth/me');
      const store = useAuthStore.getState();
      store.setTokens(tokens);
      store.setUser(user);
      store.setOnboardingComplete(user.onboarding_complete);
      store.setMustChangePassword(user.must_change_password);
      navigate('/app/onboarding', { replace: true });
    } catch (caught) {
      if (caught instanceof ApiErrorException) {
        if (caught.error.status === 409) {
          setServerError('That workspace address is already in use. Choose another address.');
        } else if (caught.error.status === 0) {
          setServerError('The TellUS service cannot be reached. Your workspace was not created.');
        } else {
          setServerError(caught.error.message);
        }
      } else {
        setServerError('Registration could not be completed. Please try again.');
      }
    }
  }

  const formErrors = submitCount
    ? Object.values(errors).map((item) => item?.message).filter((item): item is string => Boolean(item))
    : [];
  const passwordRules = [
    ['At least 12 characters', password.length >= 12],
    ['Uppercase and lowercase letters', /[a-z]/.test(password) && /[A-Z]/.test(password)],
    ['At least one number', /\d/.test(password)],
  ] as const;

  return (
    <AuthLayout>
      <AuthPanel illustration={<AuthIllustration variant="signup" />}>
        <div className="mx-auto max-w-lg">
          <p className="text-sm font-bold uppercase tracking-[0.16em] text-primary-600 dark:text-primary-400">Company registration</p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight">Create your Company workspace</h1>
          <p className="mt-3 text-sm leading-6 text-neutral-600 dark:text-neutral-400">
            This creates the Company account used to complete onboarding. Employee, manager, and external requester accounts are provisioned separately.
          </p>
          <form className="mt-8 space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
            {serverError && <AuthStatusMessage variant="error" title="Workspace not created">{serverError}</AuthStatusMessage>}
            <FormErrorSummary errors={formErrors} />
            <Input
              label="Company name"
              placeholder="Northwind Operations"
              autoComplete="organization"
              icon={<Building2 size={17} aria-hidden="true" />}
              className="h-12 rounded-xl text-base"
              error={errors.company_name?.message}
              {...register('company_name', { required: 'Company name is required', maxLength: { value: 255, message: 'Company name is too long' } })}
            />
            <Input
              label="Workspace address"
              placeholder="northwind-operations"
              helperText="Used when every member signs in. Lowercase letters, numbers, and hyphens only."
              className="h-12 rounded-xl text-base"
              error={errors.company_slug?.message}
              {...register('company_slug', {
                required: 'Workspace address is required',
                minLength: { value: 2, message: 'Workspace address must contain at least 2 characters' },
                pattern: { value: /^[a-z0-9]+(?:-[a-z0-9]+)*$/, message: 'Use lowercase letters, numbers, and single hyphens only' },
              })}
            />
            <Input
              label="Company account email"
              type="email"
              placeholder="owner@company.com"
              autoComplete="email"
              icon={<Mail size={17} aria-hidden="true" />}
              className="h-12 rounded-xl text-base"
              error={errors.email?.message}
              {...register('email', {
                required: 'Business email is required',
                pattern: { value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: 'Enter a valid business email' },
              })}
            />
            <PasswordField
              label="Password"
              autoComplete="new-password"
              error={errors.password?.message}
              {...register('password', {
                required: 'Password is required',
                minLength: { value: 12, message: 'Password must contain at least 12 characters' },
              })}
            />
            <ul className="grid gap-2 text-xs text-neutral-500 sm:grid-cols-3 dark:text-neutral-400" aria-label="Password requirements">
              {passwordRules.map(([rule, met]) => (
                <li key={rule} className="flex items-center gap-1.5">
                  <span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full ${met ? 'bg-success-100 text-success-700 dark:bg-success-900 dark:text-success-300' : 'bg-neutral-100 text-neutral-400 dark:bg-neutral-800'}`}>
                    <Check size={11} aria-hidden="true" />
                  </span>
                  {rule}
                </li>
              ))}
            </ul>
            <PasswordField
              label="Confirm password"
              autoComplete="new-password"
              error={errors.confirm_password?.message}
              {...register('confirm_password', {
                required: 'Confirm your password',
                validate: (value) => value === password || 'Password confirmation does not match',
              })}
            />
            <Button className="w-full rounded-xl" size="lg" type="submit" isLoading={isSubmitting || registration.isPending} disabled={registration.isPending}>
              Create Company workspace
            </Button>
            <p className="text-xs leading-5 text-neutral-500 dark:text-neutral-400">
              Registration creates an inactive workspace. You will authenticate immediately and complete the required Company onboarding before activation.
            </p>
          </form>
          <div className="mt-8 border-t border-neutral-200 pt-6 text-center text-sm text-neutral-600 dark:border-neutral-800 dark:text-neutral-400">
            Already have a provisioned account?{' '}
            <Link to="/login" className="font-semibold text-primary-600 hover:underline dark:text-primary-400">Sign in to your workspace</Link>
          </div>
        </div>
      </AuthPanel>
    </AuthLayout>
  );
}
