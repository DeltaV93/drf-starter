/**
 * Sign in.
 *
 * The one branch worth reading carefully is two-factor: the password step can
 * succeed and still not sign anyone in. The challenge it returns instead is
 * carried to the verification screen as a route parameter, because it is
 * exactly what that screen needs and nothing else in the app should be
 * holding it.
 */

import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useForm } from 'react-hook-form';
import { View } from 'react-native';
import { Button, Text, useTheme } from 'react-native-paper';

import { FormField } from '../components/FormField';
import { Screen, ScreenHeader } from '../components/Screen';
import { ApiError } from '../lib/api';
import { flags } from '../lib/config';
import { registerForPush } from '../lib/push';
import { safeRedirect } from '../lib/redirect';
import { useErrorMessage } from '../lib/useErrorMessage';
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
  const { t } = useTranslation();
  const { login } = useAuth();
  const toast = useToast();
  const describe = useErrorMessage();

  // Where to go once this succeeds. Defaults to the profile; an emailed
  // invitation sends people here with its own URL so the flow can resume
  // rather than ending on the wrong screen with the token gone.
  const { redirect } = useLocalSearchParams<{ redirect?: string }>();
  const destination = safeRedirect(redirect);

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
        // The destination travels with the challenge: the second factor is a
        // detour within this same flow, not the end of it.
        router.push({
          pathname: '/two-factor',
          params: { challenge: result.challenge, redirect: destination },
        });
        return;
      }

      // After sign-in, not at launch: the permission prompt is a one-shot,
      // and someone who declines it before they have an account cannot be
      // asked again from inside the app. Deliberately not awaited -- the
      // prompt must not delay the first screen.
      if (flags.push) void registerForPush();

      router.replace(destination);
    } catch (error) {
      if (error instanceof ApiError) {
        setFieldErrors({
          username: error.fieldError('username'),
          password: error.fieldError('password'),
        });
      }
      toast.error(describe(error, 'couldNotSignIn'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader title={t('welcomeBack')} />

      <FormField
        control={control}
        name="username"
        label={t('username')}
        serverError={fieldErrors.username}
        textContentType="username"
        autoComplete="username"
      />
      <FormField
        control={control}
        name="password"
        label={t('password')}
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
        {t('login')}
      </Button>

      <View style={{ marginTop: theme.spacing(3), gap: theme.spacing(0.5) }}>
        <Button mode="text" onPress={() => router.push('/reset-password')}>
          {t('forgotPassword')}
        </Button>
        <Button
          mode="text"
          onPress={() => router.push({ pathname: '/signup', params: { redirect: destination } })}
        >
          {t('createAccount')}
        </Button>
      </View>

      {flags.socialAuth ? (
        <Text
          variant="bodySmall"
          style={{ marginTop: theme.spacing(2), color: theme.colors.onSurfaceVariant }}
        >
          {t('socialOnWebsite')}
        </Text>
      ) : null}
    </Screen>
  );
}
