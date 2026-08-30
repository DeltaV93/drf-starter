/**
 * Ask for a password reset email.
 *
 * The response is identical whether or not the address exists, and this
 * screen must not undo that: showing "no account with that email" would turn
 * the endpoint into an account-enumeration oracle from the one client where
 * nobody is watching the network tab. Same rule as the website's.
 */

import { useRouter } from 'expo-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useForm } from 'react-hook-form';

import { FormField } from '../components/FormField';
import { Screen, ScreenHeader } from '../components/Screen';
import { apiCall } from '../lib/api';
import { routes } from '../lib/routes';
import { useErrorMessage } from '../lib/useErrorMessage';
import { useToast } from '../store/toast';
import { Button, Text, useTheme } from 'react-native-paper';
import type { AppTheme } from '../theme/paper';

export default function ResetPasswordScreen() {
  const theme = useTheme<AppTheme>();
  const router = useRouter();
  const { t } = useTranslation();
  const toast = useToast();
  const describe = useErrorMessage();

  const { control, handleSubmit } = useForm<{ email: string }>({ defaultValues: { email: '' } });
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  async function onSubmit({ email }: { email: string }) {
    setSubmitting(true);
    try {
      await apiCall({
        url: routes.api.auth.passwordReset(),
        method: 'POST',
        data: { email },
        errorMessage: 'Could not send the email.',
      });
      setSent(true);
    } catch (error) {
      toast.error(describe(error, 'couldNotSendEmail'));
    } finally {
      setSubmitting(false);
    }
  }

  if (sent) {
    return (
      <Screen>
        <ScreenHeader title={t('checkYourEmail')} subtitle={t('passwordResetSent')} />
        <Text
          variant="bodySmall"
          style={{ marginBottom: theme.spacing(2), color: theme.colors.onSurfaceVariant }}
        >
          {t('resetLinkOpensApp')}
        </Text>
        <Button mode="contained" onPress={() => router.replace('/login')}>
          {t('backToLogin')}
        </Button>
      </Screen>
    );
  }

  return (
    <Screen>
      <ScreenHeader title={t('resetPassword')} subtitle={t('resetPasswordHelp')} />

      <FormField
        control={control}
        name="email"
        label={t('email')}
        keyboardType="email-address"
        textContentType="emailAddress"
        autoComplete="email"
      />

      <Button
        mode="contained"
        onPress={handleSubmit(onSubmit)}
        loading={submitting}
        disabled={submitting}
      >
        {t('sendResetLink')}
      </Button>
    </Screen>
  );
}
