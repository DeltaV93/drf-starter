import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  List,
  ListItem,
  TextField,
  Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';
import { Controller, useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { ApiError, apiCall } from '../../lib/api';
import { routes } from '../../lib/routes';
import { usePasswordValidation } from '../../hooks/usePasswordValidation';
import { useToast } from '../../store/toast';

interface ConfirmPasswordForm {
  password: string;
  password_confirm: string;
}

type TokenState = 'checking' | 'valid' | 'invalid';

export default function ConfirmNewPasswordPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const { uid, token } = useParams<{ uid: string; token: string }>();
  // Derived at mount rather than set from inside the effect: a synchronous
  // setState in an effect body causes a cascading re-render.
  const [tokenState, setTokenState] = useState<TokenState>(() =>
    uid && token ? 'checking' : 'invalid',
  );

  const {
    control,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<ConfirmPasswordForm>({ defaultValues: { password: '', password_confirm: '' } });

  // useWatch subscribes through `control`, which is stable; watch() is not.
  const password = useWatch({ control, name: 'password' });
  const passwordConfirm = useWatch({ control, name: 'password_confirm' });
  const { isValid, errors } = usePasswordValidation(password, passwordConfirm);

  useEffect(() => {
    if (!uid || !token) return;

    let cancelled = false;

    (async () => {
      try {
        const envelope = await apiCall<{ is_valid: boolean }>({
          method: 'GET',
          url: routes.api.auth.passwordResetValidate(uid, token),
        });
        if (cancelled) return;
        setTokenState(envelope.data?.is_valid ? 'valid' : 'invalid');
      } catch {
        if (cancelled) return;
        setTokenState('invalid');
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [uid, token]);

  const onSubmit = async (values: ConfirmPasswordForm) => {
    try {
      await apiCall({
        method: 'POST',
        url: routes.api.auth.passwordResetConfirm(),
        data: { uid, token, ...values },
        errorMessage: t('passwordResetError'),
      });
      toast.success(t('passwordResetSuccess'));
      navigate('/login');
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t('genericError'));
    }
  };

  if (tokenState === 'checking') {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (tokenState === 'invalid') {
    return (
      <Container maxWidth="xs">
        <Box sx={{ mt: 8 }}>
          <Alert severity="error">{t('invalidResetLink')}</Alert>
          <Button component={Link} to="/reset-password" fullWidth sx={{ mt: 2 }}>
            {t('requestNewLink')}
          </Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="xs">
      <Box sx={{ mt: 8 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          {t('resetPassword')}
        </Typography>

        <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
          <Controller
            name="password"
            control={control}
            rules={{ required: t('passwordRequired') }}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                id="password"
                type="password"
                label={t('newPassword')}
                autoComplete="new-password"
                autoFocus
                fullWidth
                margin="normal"
                error={!!error}
                helperText={error?.message}
              />
            )}
          />
          <Controller
            name="password_confirm"
            control={control}
            rules={{ required: t('confirmPasswordRequired') }}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                id="password_confirm"
                type="password"
                label={t('confirmPassword')}
                autoComplete="new-password"
                fullWidth
                margin="normal"
                error={!!error}
                helperText={error?.message}
              />
            )}
          />

          {password.length > 0 && errors.length > 0 && (
            <List dense>
              {errors.map((message) => (
                <ListItem key={message} disableGutters>
                  <Typography variant="body2" color="error">
                    {message}
                  </Typography>
                </ListItem>
              ))}
            </List>
          )}

          <Button
            type="submit"
            fullWidth
            variant="contained"
            disabled={!isValid || isSubmitting}
            sx={{ mt: 3 }}
          >
            {t('resetPassword')}
          </Button>
        </Box>
      </Box>
    </Container>
  );
}
