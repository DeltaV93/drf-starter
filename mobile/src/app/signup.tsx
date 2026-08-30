/**
 * Create an account.
 *
 * The password rules come from `@app/shared/passwordValidation`, which the
 * website uses too -- they approximate Django's AUTH_PASSWORD_VALIDATORS, and
 * two copies of an approximation drift into one client rejecting what the
 * other accepts.
 */

import { usePasswordValidation } from '@app/shared/passwordValidation';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useForm, useWatch } from 'react-hook-form';
import { View } from 'react-native';
import { Button, HelperText, useTheme } from 'react-native-paper';

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

interface SignUpForm {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  password2: string;
}

const EMPTY: SignUpForm = {
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  password2: '',
};

export default function SignUpScreen() {
  const theme = useTheme<AppTheme>();
  const router = useRouter();
  const { t } = useTranslation();
  const { register } = useAuth();
  const toast = useToast();
  const describe = useErrorMessage();

  // Same contract as the sign-in screen: an invitation that sent someone here
  // to create an account has to get them back to accepting it.
  const { redirect } = useLocalSearchParams<{ redirect?: string }>();
  const destination = safeRedirect(redirect);

  const { control, handleSubmit } = useForm<SignUpForm>({ defaultValues: EMPTY });
  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | undefined>>({});

  const password = useWatch({ control, name: 'password' });
  const password2 = useWatch({ control, name: 'password2' });
  const { isValid, errors } = usePasswordValidation(password, password2);

  async function onSubmit(values: SignUpForm) {
    setSubmitting(true);
    setFieldErrors({});

    try {
      await register(values);
      if (flags.push) void registerForPush();
      toast.success(t('signupSuccess'));
      router.replace(destination);
    } catch (error) {
      if (error instanceof ApiError) {
        setFieldErrors({
          username: error.fieldError('username'),
          email: error.fieldError('email'),
          password: error.fieldError('password'),
          password2: error.fieldError('password2'),
        });
      }
      toast.error(describe(error, 'couldNotCreateAccount'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader title={t('createAccount')} />

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
        name="email"
        label={t('email')}
        serverError={fieldErrors.email}
        keyboardType="email-address"
        textContentType="emailAddress"
        autoComplete="email"
      />
      <FormField
        control={control}
        name="first_name"
        label={t('firstName')}
        autoCapitalize="words"
      />
      <FormField control={control} name="last_name" label={t('lastName')} autoCapitalize="words" />
      <FormField
        control={control}
        name="password"
        label={t('password')}
        serverError={fieldErrors.password}
        secureTextEntry
        textContentType="newPassword"
        autoComplete="new-password"
      />
      <FormField
        control={control}
        name="password2"
        label={t('confirmPassword')}
        serverError={fieldErrors.password2}
        secureTextEntry
        textContentType="newPassword"
        autoComplete="new-password"
      />

      {/* Shown only once there is something to check, so the rules are not a
          wall of red on an empty form. */}
      {password.length > 0
        ? errors.map((message) => (
            <HelperText key={message} type="error" visible>
              {message}
            </HelperText>
          ))
        : null}

      <View style={{ marginTop: theme.spacing(2) }}>
        <Button
          mode="contained"
          onPress={handleSubmit(onSubmit)}
          loading={submitting}
          disabled={submitting || !isValid}
        >
          {t('createAccountAction')}
        </Button>
        <Button
          mode="text"
          onPress={() => router.push({ pathname: '/login', params: { redirect: destination } })}
        >
          {t('alreadyHaveAccount')}
        </Button>
      </View>
    </Screen>
  );
}
