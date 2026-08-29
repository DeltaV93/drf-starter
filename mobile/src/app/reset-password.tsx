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
import { useForm } from 'react-hook-form';

import { FormField } from '../components/FormField';
import { Screen, ScreenHeader } from '../components/Screen';
import { ApiError, apiCall } from '../lib/api';
import { routes } from '../lib/routes';
import { useToast } from '../store/toast';
import { Button, Text, useTheme } from 'react-native-paper';
import type { AppTheme } from '../theme/paper';

export default function ResetPasswordScreen() {
  const theme = useTheme<AppTheme>();
  const router = useRouter();
  const toast = useToast();

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
      toast.error(error instanceof ApiError ? error.message : 'Could not send the email.');
    } finally {
      setSubmitting(false);
    }
  }

  if (sent) {
    return (
      <Screen>
        <ScreenHeader
          title="Check your email"
          subtitle="If an account exists for that address, we have sent a link to reset the password."
        />
        <Text
          variant="bodySmall"
          style={{ marginBottom: theme.spacing(2), color: theme.colors.onSurfaceVariant }}
        >
          Opening that link on this device brings you straight back here to
          choose a new password.
        </Text>
        <Button mode="contained" onPress={() => router.replace('/login')}>
          Back to sign in
        </Button>
      </Screen>
    );
  }

  return (
    <Screen>
      <ScreenHeader
        title="Reset your password"
        subtitle="We will email you a link to choose a new one."
      />

      <FormField
        control={control}
        name="email"
        label="Email"
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
        Send the link
      </Button>
    </Screen>
  );
}
