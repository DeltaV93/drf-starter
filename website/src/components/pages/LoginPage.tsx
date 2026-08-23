import { Alert, Box, Button, Container, TextField, Typography } from '@mui/material';
import { Controller, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { ApiError } from '../../lib/api';
import { useAuth } from '../../store/auth';
import { useToast } from '../../store/toast';

interface LoginForm {
  username: string;
  password: string;
}

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const { login } = useAuth();
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting, errors },
  } = useForm<LoginForm>({ defaultValues: { username: '', password: '' } });

  // Send the user back where ProtectedRoute intercepted them.
  const redirectTo = (location.state as { from?: { pathname: string } } | null)?.from?.pathname;

  const onSubmit = async (values: LoginForm) => {
    try {
      await login(values);
      toast.success(t('loginSuccess'));
      navigate(redirectTo ?? '/profile', { replace: true });
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

  return (
    <Container maxWidth="xs">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Typography variant="h4" component="h1" gutterBottom>
          {t('login')}
        </Typography>

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
