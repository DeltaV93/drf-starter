import { Alert, Box, Button, Container, TextField, Typography } from '@mui/material';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { ApiError, apiCall } from '../../lib/api';
import { routes } from '../../lib/routes';
import { useToast } from '../../store/toast';

interface PasswordResetForm {
  email: string;
}

export default function PasswordResetPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const [submitted, setSubmitted] = useState(false);
  const {
    control,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<PasswordResetForm>({ defaultValues: { email: '' } });

  const onSubmit = async (values: PasswordResetForm) => {
    try {
      await apiCall({
        url: routes.api.auth.passwordReset(),
        method: 'POST',
        data: values,
        errorMessage: t('passwordResetError'),
      });
      // The backend answers the same whether or not the address exists, and
      // so does this screen -- redirecting to /login on success would leak
      // which addresses are registered.
      setSubmitted(true);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t('genericError'));
    }
  };

  if (submitted) {
    return (
      <Container maxWidth="xs">
        <Box sx={{ mt: 8 }}>
          <Alert severity="success">{t('passwordResetSent')}</Alert>
          <Button component={Link} to="/login" fullWidth sx={{ mt: 2 }}>
            {t('backToLogin')}
          </Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="xs">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Typography variant="h4" component="h1" gutterBottom>
          {t('resetPassword')}
        </Typography>

        <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate sx={{ width: '100%' }}>
          <Controller
            name="email"
            control={control}
            rules={{
              required: t('emailRequired'),
              pattern: { value: /^\S+@\S+\.\S+$/, message: t('invalidEmail') },
            }}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                id="email"
                type="email"
                label={t('email')}
                autoComplete="email"
                autoFocus
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
            {t('sendResetLink')}
          </Button>
        </Box>

        <Button component={Link} to="/login">
          {t('backToLogin')}
        </Button>
      </Box>
    </Container>
  );
}
