import { Alert, Box, Button, Container, Divider, Stack, TextField, Typography } from '@mui/material';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';

import { ApiError } from '../../lib/api';
import { routes } from '../../lib/routes';
import { useAuth } from '../../store/auth';
import { useToast } from '../../store/toast';

interface LoginForm {
  username: string;
  password: string;
}

interface CodeForm {
  code: string;
}

const SOCIAL_AUTH_ENABLED = import.meta.env.VITE_SOCIAL_AUTH_ENABLED === 'true';

// Keep in step with SOCIAL_AUTH_PROVIDERS on the backend, which only advertises
// providers whose key is configured.
const PROVIDER_LABELS: Record<string, string> = {
  'google-oauth2': 'Google',
  'linkedin-oauth2': 'LinkedIn',
};

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const { login, verifyTwoFactor } = useAuth();
  const [searchParams] = useSearchParams();
  // The password step succeeded but a second factor is outstanding. There is
  // no session yet -- only the pending state the backend holds.
  const [awaitingCode, setAwaitingCode] = useState(false);

  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting, errors },
  } = useForm<LoginForm>({ defaultValues: { username: '', password: '' } });

  const codeForm = useForm<CodeForm>({ defaultValues: { code: '' } });

  // Send the user back where ProtectedRoute intercepted them.
  const redirectTo = (location.state as { from?: { pathname: string } } | null)?.from?.pathname;

  // social_django redirects here with a message when the pipeline refuses --
  // most often because the email already belongs to a password account.
  const providerError = searchParams.get('message');

  const finish = () => {
    toast.success(t('loginSuccess'));
    navigate(redirectTo ?? '/profile', { replace: true });
  };

  const onSubmit = async (values: LoginForm) => {
    try {
      const result = await login(values);
      if (result.status === 'two-factor-required') {
        setAwaitingCode(true);
        return;
      }
      finish();
    } catch (error) {
      if (error instanceof ApiError) {
        // The backend answers identically for unknown user and wrong
        // password, so surface it as a form-level error, not a field one.
        setError('root', { message: error.message });
        toast.error(error.message);
        return;
      }
      toast.error(t('genericError'));
    }
  };

  const onVerify = async (values: CodeForm) => {
    try {
      await verifyTwoFactor(values.code);
      finish();
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t('genericError');
      codeForm.setError('root', { message });
      toast.error(message);
    }
  };

  if (awaitingCode) {
    return (
      <Container maxWidth="xs">
        <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <Typography variant="h5" component="h1" gutterBottom>
            {t('twoFactorTitle')}
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 2, textAlign: 'center' }}>
            {t('twoFactorPrompt')}
          </Typography>

          <Box
            component="form"
            onSubmit={codeForm.handleSubmit(onVerify)}
            noValidate
            sx={{ width: '100%' }}
          >
            {codeForm.formState.errors.root && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {codeForm.formState.errors.root.message}
              </Alert>
            )}

            <Controller
              name="code"
              control={codeForm.control}
              rules={{ required: t('twoFactorCodeRequired') }}
              render={({ field, fieldState: { error } }) => (
                <TextField
                  {...field}
                  id="code"
                  label={t('twoFactorCode')}
                  // one-time-code lets a phone offer the SMS/authenticator autofill.
                  autoComplete="one-time-code"
                  inputMode="text"
                  autoFocus
                  fullWidth
                  margin="normal"
                  error={!!error}
                  helperText={error?.message ?? t('twoFactorHelp')}
                />
              )}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              disabled={codeForm.formState.isSubmitting}
              sx={{ mt: 3, mb: 2 }}
            >
              {codeForm.formState.isSubmitting ? t('signingIn') : t('twoFactorVerify')}
            </Button>
          </Box>

          <Button onClick={() => setAwaitingCode(false)}>{t('backToLogin')}</Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="xs">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Typography variant="h4" component="h1" gutterBottom>
          {t('login')}
        </Typography>

        {providerError && (
          <Alert severity="error" sx={{ mb: 2, width: '100%' }}>
            {providerError}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate sx={{ width: '100%' }}>
          {errors.root && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {errors.root.message}
            </Alert>
          )}

          <Controller
            name="username"
            control={control}
            rules={{ required: t('usernameRequired') }}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                id="username"
                label={t('username')}
                autoComplete="username"
                autoFocus
                fullWidth
                margin="normal"
                error={!!error}
                helperText={error?.message}
              />
            )}
          />

          <Controller
            name="password"
            control={control}
            rules={{ required: t('passwordRequired') }}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                id="password"
                type="password"
                label={t('password')}
                autoComplete="current-password"
                fullWidth
                margin="normal"
                error={!!error}
                helperText={error?.message}
              />
            )}
          />

          <Button
            type="submit"
            fullWidth
            variant="contained"
            disabled={isSubmitting}
            sx={{ mt: 3, mb: 2 }}
          >
            {isSubmitting ? t('signingIn') : t('login')}
          </Button>
        </Box>

        {SOCIAL_AUTH_ENABLED && (
          <Box sx={{ width: '100%', mt: 1 }}>
            <Divider sx={{ my: 2 }}>{t('orContinueWith')}</Divider>
            <Stack spacing={1}>
              {Object.entries(PROVIDER_LABELS).map(([provider, label]) => (
                <Button
                  key={provider}
                  fullWidth
                  variant="outlined"
                  /* A full page navigation, not an XHR: the provider redirects
                     the browser and needs to set its own cookies. */
                  href={routes.api.social.begin(provider)}
                >
                  {label}
                </Button>
              ))}
            </Stack>
          </Box>
        )}

        <Button component={Link} to="/reset-password">
          {t('forgotPassword')}
        </Button>
        <Button component={Link} to="/signup">
          {t('needAnAccount')}
        </Button>
      </Box>
    </Container>
  );
}
