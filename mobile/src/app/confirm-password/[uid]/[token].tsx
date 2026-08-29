/**
 * Choose a new password, from an emailed reset link.
 *
 * `/confirm-password/<uid>/<token>` -- the filename is the routing, and the
 * path is the one the backend emails and the association documents claim.
 * See the note in `verify-email/[uid]/[token].tsx`.
 */

import { usePasswordValidation } from '@app/shared/passwordValidation';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { Button, HelperText } from 'react-native-paper';

import { FormField } from '../../../components/FormField';
import { Screen, ScreenHeader } from '../../../components/Screen';
import { ApiError, apiCall } from '../../../lib/api';
import { routes } from '../../../lib/routes';
import { useToast } from '../../../store/toast';

interface ConfirmForm {
  password: string;
  password_confirm: string;
}

export default function ConfirmPasswordScreen() {
  const router = useRouter();
  const { uid, token } = useLocalSearchParams<{ uid: string; token: string }>();
  const toast = useToast();

  const { control, handleSubmit } = useForm<ConfirmForm>({
    defaultValues: { password: '', password_confirm: '' },
  });
  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | undefined>>({});

  const password = useWatch({ control, name: 'password' });
  const confirmation = useWatch({ control, name: 'password_confirm' });
  const { isValid, errors } = usePasswordValidation(password, confirmation);

  async function onSubmit(values: ConfirmForm) {
    setSubmitting(true);
    setFieldErrors({});

    try {
      await apiCall({
        url: routes.api.auth.passwordResetConfirm(),
        method: 'POST',
        data: { uid, token, ...values },
        errorMessage: 'Could not change your password.',
      });

      // Straight to sign-in rather than signing them in here. The reset
      // endpoint establishes nothing this client can use -- it has no session
      // -- and a screen that appeared to succeed and then showed a signed-out
      // app would be worse than asking for the new password once.
      toast.success('Password changed. Sign in with your new password.');
      router.replace('/login');
    } catch (error) {
      if (error instanceof ApiError) {
        setFieldErrors({
          password: error.fieldError('password'),
          password_confirm: error.fieldError('password_confirm'),
        });
        toast.error(error.message);
      } else {
        toast.error('Could not change your password.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader title="Choose a new password" />

      <FormField
        control={control}
        name="password"
        label="New password"
        serverError={fieldErrors.password}
        secureTextEntry
        textContentType="newPassword"
        autoComplete="new-password"
      />
      <FormField
        control={control}
        name="password_confirm"
        label="Confirm new password"
        serverError={fieldErrors.password_confirm}
        secureTextEntry
        textContentType="newPassword"
        autoComplete="new-password"
      />

      {password.length > 0
        ? errors.map((message) => (
            <HelperText key={message} type="error" visible>
              {message}
            </HelperText>
          ))
        : null}

      <Button
        mode="contained"
        onPress={handleSubmit(onSubmit)}
        loading={submitting}
        disabled={submitting || !isValid}
      >
        Change password
      </Button>
    </Screen>
  );
}
