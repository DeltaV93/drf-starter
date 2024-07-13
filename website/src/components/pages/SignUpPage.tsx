import React from 'react';
import { useForm, Controller } from 'react-hook-form';
import { TextField, Button, Container, Box, Typography, Link } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAtom } from 'jotai';
import { authAtom } from '../../store/auth';
import { apiCall } from '../../utils/api';

interface SignUpForm {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

const SignUpPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [, dispatch] = useAtom(authAtom().authActions)
  const { control, handleSubmit, watch } = useForm<SignUpForm>();

  const onSubmit = async (data: SignUpForm) => {
    try {
      const response = await apiCall({
        method: 'POST',
        url: 'https://your-api-url.com/signup', // Replace with your actual signup endpoint
        data: {
          name: data.name,
          email: data.email,
          password: data.password,
        },
        successMessage: t('signupSuccess'),
        errorMessage: t('signupError'),
      });

      // Assuming the API returns user data and a token upon successful registration
      dispatch({
        type: 'LOGIN',
        payload: {
          user: response.data.user,
          token: response.data.token
        }
      });

      navigate('/profile');
    } catch (error) {
      console.error('Signup error:', error);
      // Error is already handled by apiCall, so we don't need to show another toast here
    }
  };

  return (
    <Container maxWidth="xs">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Typography component="h1" variant="h5">
          {t('signup')}
        </Typography>
        <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate sx={{ mt: 1 }}>
          <Controller
            name="name"
            control={control}
            defaultValue=""
            rules={{ required: t('nameRequired') }}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                margin="normal"
                required
                fullWidth
                id="name"
                label={t('name')}
                autoComplete="name"
                autoFocus
                error={!!error}
                helperText={error?.message}
              />
            )}
          />
          <Controller
            name="email"
            control={control}
            defaultValue=""
            rules={{
              required: t('emailRequired'),
              pattern: {
                value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                message: t('invalidEmail')
              }
            }}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                margin="normal"
                required
                fullWidth
                id="email"
                label={t('email')}
                autoComplete="email"
                error={!!error}
                helperText={error?.message}
              />
            )}
          />
          <Controller
            name="password"
            control={control}
            defaultValue=""
            rules={{
              required: t('passwordRequired'),
              minLength: {
                value: 8,
                message: t('passwordTooShort')
              }
            }}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                margin="normal"
                required
                fullWidth
                name="password"
                label={t('password')}
                type="password"
                id="password"
                autoComplete="new-password"
                error={!!error}
                helperText={error?.message}
              />
            )}
          />
          <Controller
            name="confirmPassword"
            control={control}
            defaultValue=""
            rules={{
              required: t('confirmPasswordRequired'),
              validate: (value) => value === watch('password') || t('passwordsDontMatch')
            }}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                margin="normal"
                required
                fullWidth
                name="confirmPassword"
                label={t('confirmPassword')}
                type="password"
                id="confirmPassword"
                error={!!error}
                helperText={error?.message}
              />
            )}
          />
          <Button
            type="submit"
            fullWidth
            variant="contained"
            sx={{ mt: 3, mb: 2 }}
          >
            {t('signup')}
          </Button>
          <Box sx={{ textAlign: 'center' }}>
            <Button color="primary" variant="text" onClick={() => navigate("/login")}>
              {t('alreadyHaveAccount')}
            </Button>
          </Box>
        </Box>
      </Box>
    </Container>
  );
};

export default SignUpPage;