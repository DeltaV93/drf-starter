/**
 * The second step of a sign-in that stopped for a second factor.
 *
 * The challenge arrives as a route parameter from the sign-in screen. It is
 * held nowhere else and never stored: it is redeemable for a session, it
 * expires in minutes, and putting it in the keystore would give it a lifetime
 * it does not deserve.
 *
 * Arriving here without one -- a deep link, or a reload in development --
 * sends the user back to sign in rather than showing a form that cannot work.
 */

import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Button, Text, useTheme } from 'react-native-paper';

import { FormField } from '../components/FormField';
import { Screen, ScreenHeader } from '../components/Screen';
import { ApiError } from '../lib/api';
import { flags } from '../lib/config';
import { registerForPush } from '../lib/push';
import { useAuth } from '../store/auth';
import { useToast } from '../store/toast';
import type { AppTheme } from '../theme/paper';

export default function TwoFactorScreen() {
  const theme = useTheme<AppTheme>();
  const router = useRouter();
  const { challenge } = useLocalSearchParams<{ challenge?: string }>();
  const { verifyTwoFactor } = useAuth();
  const toast = useToast();

  const { control, handleSubmit } = useForm<{ code: string }>({ defaultValues: { code: '' } });
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit({ code }: { code: string }) {
    if (!challenge) return;
    setSubmitting(true);

    try {
      await verifyTwoFactor(challenge, code);
      if (flags.push) void registerForPush();
      router.replace('/profile');
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'That code was not accepted.');
    } finally {
      setSubmitting(false);
    }
  }

  if (!challenge) {
    return (
      <Screen>
        <ScreenHeader
          title="Start again"
          subtitle="This verification is no longer available. Sign in to get a new code."
        />
        <Button mode="contained" onPress={() => router.replace('/login')}>
          Back to sign in
        </Button>
      </Screen>
    );
  }

  return (
    <Screen>
      <ScreenHeader
        title="Two-step verification"
        subtitle="Enter the code from your authenticator app."
      />

      <FormField
        control={control}
        name="code"
        label="Code"
        keyboardType="number-pad"
        textContentType="oneTimeCode"
        autoComplete="one-time-code"
      />

      <Button
        mode="contained"
        onPress={handleSubmit(onSubmit)}
        loading={submitting}
        disabled={submitting}
      >
        Verify
      </Button>

      <Text
        variant="bodySmall"
        style={{ marginTop: theme.spacing(2), color: theme.colors.onSurfaceVariant }}
      >
        Lost your authenticator? Enter one of your recovery codes instead.
      </Text>
    </Screen>
  );
}
