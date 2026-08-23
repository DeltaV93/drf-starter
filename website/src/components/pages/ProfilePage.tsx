import {
  Alert,
  Box,
  Button,
  Container,
  Divider,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { Controller, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';

import { ApiError, apiCall } from '../../lib/api';
import { routes } from '../../lib/routes';
import type { User } from '../../lib/types';
import { useAuth } from '../../store/auth';
import { useToast } from '../../store/toast';

interface ProfileForm {
  first_name: string;
  last_name: string;
  phone_number: string;
}

export default function ProfilePage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { user, refresh } = useAuth();
  const {
    control,
    handleSubmit,
    formState: { isSubmitting, isDirty },
  } = useForm<ProfileForm>({
    values: {
      first_name: user?.first_name ?? '',
      last_name: user?.last_name ?? '',
      phone_number: user?.phone_number ?? '',
    },
  });

  const onSubmit = async (values: ProfileForm) => {
    try {
      await apiCall<User>({
        url: routes.api.users.me(),
        method: 'PATCH',
        data: values,
        errorMessage: t('profileUpdateError'),
      });
      await refresh();
      toast.success(t('profileUpdated'));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t('genericError'));
    }
  };

  const resendVerification = async () => {
    try {
      await apiCall({
        url: routes.api.auth.resendVerification(),
        method: 'POST',
        data: { email: user?.email },
      });
      toast.success(t('verificationResent'));
    } catch {
      toast.error(t('genericError'));
    }
  };

  if (!user) return null;

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          {t('profile')}
        </Typography>

        {!user.email_verified && (
          <Alert
            severity="warning"
            sx={{ mb: 3 }}
            action={
              <Button color="inherit" size="small" onClick={resendVerification}>
                {t('resend')}
              </Button>
            }
          >
            {t('emailNotVerified')}
          </Alert>
        )}

        <Stack spacing={1} sx={{ mb: 3 }}>
          <Typography variant="body2" color="text.secondary">
            {t('username')}: {user.username}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t('email')}: {user.email}
          </Typography>
        </Stack>

        <Divider sx={{ mb: 3 }} />

        <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
          <Controller
            name="first_name"
            control={control}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                id="first_name"
                label={t('firstName')}
                fullWidth
                margin="normal"
                error={!!error}
                helperText={error?.message}
              />
            )}
          />
          <Controller
            name="last_name"
            control={control}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                id="last_name"
                label={t('lastName')}
                fullWidth
                margin="normal"
                error={!!error}
                helperText={error?.message}
              />
            )}
          />
          <Controller
            name="phone_number"
            control={control}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                id="phone_number"
                label={t('phoneNumber')}
                fullWidth
                margin="normal"
                error={!!error}
                helperText={error?.message}
              />
            )}
          />

          <Button
            type="submit"
            variant="contained"
            disabled={isSubmitting || !isDirty}
            sx={{ mt: 2 }}
          >
            {t('saveChanges')}
          </Button>
        </Box>
      </Box>
    </Container>
  );
}
