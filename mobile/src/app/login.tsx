/**
 * Sign in.
 *
 * The one branch worth reading carefully is two-factor: the password step can
 * succeed and still not sign anyone in. The challenge it returns instead is
 * carried to the verification screen as a route parameter, because it is
 * exactly what that screen needs and nothing else in the app should be
 * holding it.
 */

import { useRouter } from 'expo-router';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { View } from 'react-native';
import { Button, Text, useTheme } from 'react-native-paper';

import { FormField } from '../components/FormField';
import { Screen, ScreenHeader } from '../components/Screen';
import { ApiError } from '../lib/api';
import { flags } from '../lib/config';
import { registerForPush } from '../lib/push';
import { useAuth } from '../store/auth';
import { useToast } from '../store/toast';
import type { AppTheme } from '../theme/paper';

interface LoginForm {
  username: string;
  password: string;
}

export default function LoginScreen() {
  const theme = useTheme<AppTheme>();
  const router = useRouter();
  const { login } = useAuth();
  const toast = useToast();

  const { control, handleSubmit } = useForm<LoginForm>({
    defaultValues: { username: '', password: '' },
  });
  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | undefined>>({});

  async function onSubmit(values: LoginForm) {
    setSubmitting(true);
    setFieldErrors({});

    try {
      const result = await login(values);

      if (result.status === 'two-factor-required') {
        router.push({ pathname: '/two-factor', params: { challenge: result.challenge } });
        return;
      }

      // After sign-in, not at launch: the permission prompt is a one-shot,
      // and someone who declines it before they have an account cannot be
      // asked again from inside the app. Deliberately not awaited -- the
      // prompt must not delay the first screen.
      if (flags.push) void registerForPush();

      router.replace('/profile');
    } catch (error) {
      if (error instanceof ApiError) {
        setFieldErrors({
          username: error.fieldError('username'),
          password: error.fieldError('password'),
        });
        toast.error(error.message);
      } else {
        toast.error('Could not sign you in.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader title="Welcome back" />

      <FormField
        control={control}
        name="username"
        label="Username"
        serverError={fieldErrors.username}
        textContentType="username"
        autoComplete="username"
      />
      <FormField
        control={control}
        name="password"
        label="Password"
        serverError={fieldErrors.password}
        secureTextEntry
        textContentType="password"
        autoComplete="current-password"
      />

      <Button
        mode="contained"
        onPress={handleSubmit(onSubmit)}
        loading={submitting}
        disabled={submitting}
        style={{ marginTop: theme.spacing(1) }}
      >
        Sign in
      </Button>

      <View style={{ marginTop: theme.spacing(3), gap: theme.spacing(0.5) }}>
        <Button mode="text" onPress={() => router.push('/reset-password')}>
          Forgot your password?
        </Button>
        <Button mode="text" onPress={() => router.push('/signup')}>
          Create an account
        </Button>
      </View>

      {flags.socialAuth ? (
        <Text
          variant="bodySmall"
          style={{ marginTop: theme.spacing(2), color: theme.colors.onSurfaceVariant }}
        >
          Signing in with Google or LinkedIn is available on the website. Native
          provider sign-in needs an authorization-code exchange the backend does
          not offer yet — see docs/mobile.md.
        </Text>
      ) : null}
    </Screen>
  );
}
