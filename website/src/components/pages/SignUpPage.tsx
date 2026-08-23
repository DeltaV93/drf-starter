import { Box, Button, Container, TextField, Typography } from '@mui/material';
import { Controller, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';

import { ApiError } from '../../lib/api';
import { useAuth, type RegistrationDetails } from '../../store/auth';
import { useToast } from '../../store/toast';

const FIELDS = [
  { name: 'first_name', label: 'firstName', autoComplete: 'given-name' },
  { name: 'last_name', label: 'lastName', autoComplete: 'family-name' },
  { name: 'username', label: 'username', autoComplete: 'username' },
  { name: 'email', label: 'email', autoComplete: 'email', type: 'email' },
] as const;

export default function SignUpPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const { register } = useAuth();
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting },
  } = useForm<RegistrationDetails>({
    defaultValues: {
      first_name: '',
      last_name: '',
      username: '',
      email: '',
      password: '',
      password2: '',
    },
  });

  const onSubmit = async (values: RegistrationDetails) => {
    try {
      await register(values);
      toast.success(t('signupSuccess'));
      navigate('/profile');
    } catch (error) {
      if (error instanceof ApiError) {
        // Map the backend's per-field errors onto the form so the user sees
        // "that username is taken" next to the username box.
        let matched = false;
        for (const field of Object.keys(values) as (keyof RegistrationDetails)[]) {
          const message = error.fieldError(field);
          if (message) {
            setError(field, { message });
            matched = true;
          }
        }
        if (!matched) setError('root', { message: error.message });
        toast.error(error.message);
        return;
      }
      toast.error(t('genericError'));
    }
  };

  return (
    <Container maxWidth="xs">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Typography component="h1" variant="h4" gutterBottom>
          {t('signup')}
        </Typography>

        {/* One form. The previous version nested a second <form> inside this
            one, which is invalid HTML and split the fields across two forms. */}
        <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate sx={{ width: '100%' }}>
          {FIELDS.map((spec, index) => (
            <Controller
              key={spec.name}
              name={spec.name}
              control={control}
              rules={{ required: t(`${spec.label}Required`) }}
              render={({ field, fieldState: { error } }) => (
                <TextField
                  {...field}
                  id={spec.name}
                  type={'type' in spec ? spec.type : 'text'}
                  label={t(spec.label)}
                  autoComplete={spec.autoComplete}
                  autoFocus={index === 0}
                  required
                  fullWidth
                  margin="normal"
                  error={!!error}
                  helperText={error?.message}
                />
              )}
            />
          ))}

          <Controller
            name="password"
            control={control}
            rules={{
              required: t('passwordRequired'),
              minLength: { value: 8, message: t('passwordTooShort') },
            }}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                id="password"
                type="password"
                label={t('password')}
                autoComplete="new-password"
                required
                fullWidth
                margin="normal"
                error={!!error}
                helperText={error?.message}
              />
            )}
          />

          <Controller
            name="password2"
            control={control}
            rules={{
              required: t('confirmPasswordRequired'),
              // formValues comes from RHF itself, so this needs no watch()
              // subscription to stay in sync.
              validate: (value, formValues) =>
                value === formValues.password || t('passwordsDontMatch'),
            }}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                id="password2"
                type="password"
                label={t('confirmPassword')}
                autoComplete="new-password"
                required
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
            {isSubmitting ? t('creatingAccount') : t('signup')}
          </Button>
        </Box>

        <Button component={Link} to="/login">
          {t('alreadyHaveAccount')}
        </Button>
      </Box>
    </Container>
  );
}
