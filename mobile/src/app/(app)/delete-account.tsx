/**
 * Deleting your account, from inside the app.
 *
 * This screen exists because it has to. Apple's guideline 5.1.1(v) requires
 * an app that lets you create an account to let you delete it *in the app* --
 * not on a website it links to. An earlier version of this project sent
 * people to the website and called that a considered decision; it was a
 * review rejection waiting to happen.
 *
 * The friction is deliberate and is not the same thing as hiding it. The
 * action is one tap from Settings, and then asks for the password and a
 * confirmation -- because it is irreversible, and because the backend asks
 * for the password anyway.
 *
 * What "delete" means here is anonymisation: `utils/gdpr_utils.py` overwrites
 * the personal fields, unsets the password, deactivates the row and
 * blacklists every outstanding token. Related records survive, so an invoice
 * still has an author. The screen says so rather than promising an erasure
 * the backend does not perform.
 */

import { useRouter } from 'expo-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';
import { Button, Dialog, Portal, Text, TextInput, useTheme } from 'react-native-paper';

import { Screen, ScreenHeader } from '../../components/Screen';
import { apiCall } from '../../lib/api';
import { flags } from '../../lib/config';
import { unregisterFromPush } from '../../lib/push';
import { routes } from '../../lib/routes';
import { useErrorMessage } from '../../lib/useErrorMessage';
import { useAuth } from '../../store/auth';
import { useOrganizations } from '../../store/organization';
import { useToast } from '../../store/toast';
import type { AppTheme } from '../../theme/paper';

export default function DeleteAccountScreen() {
  const theme = useTheme<AppTheme>();
  const router = useRouter();
  const { t } = useTranslation();
  const { logout } = useAuth();
  const { forget } = useOrganizations();
  const toast = useToast();
  const describe = useErrorMessage();

  const [password, setPassword] = useState('');
  const [reason, setReason] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function deleteAccount() {
    setConfirming(false);
    setSubmitting(true);

    try {
      await apiCall({
        url: routes.api.auth.deleteAccount(),
        method: 'POST',
        data: { password, reason },
      });

      // The backend deactivates the account and blacklists its tokens, so
      // nothing this app holds still works. Clearing locally is what stops
      // the next launch from showing a signed-in shell that 401s on every
      // screen.
      //
      // Unregistering first, while the credential is still attached: after
      // `logout()` there is nothing to authorise the call with. It will
      // likely fail anyway now the account is inactive, and it is written to
      // tolerate that.
      if (flags.push) await unregisterFromPush();
      await forget();
      await logout();

      toast.success(t('accountDeleted'));
      router.replace('/');
    } catch (error) {
      toast.error(describe(error, 'couldNotDeleteAccount'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader title={t('deleteAccount')} subtitle={t('deleteAccountWhat')} />

      <Text
        variant="bodyMedium"
        style={{ marginBottom: theme.spacing(3), color: theme.colors.onSurfaceVariant }}
      >
        {t('deleteAccountIrreversible')}
      </Text>

      <TextInput
        mode="outlined"
        label={t('yourPassword')}
        accessibilityLabel={t('yourPassword')}
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        textContentType="password"
        autoComplete="current-password"
      />

      <TextInput
        mode="outlined"
        label={t('deleteAccountReason')}
        accessibilityLabel={t('deleteAccountReason')}
        value={reason}
        onChangeText={setReason}
        multiline
        numberOfLines={3}
        style={{ marginTop: theme.spacing(1) }}
      />

      <View style={{ marginTop: theme.spacing(3), gap: theme.spacing(1) }}>
        <Button
          mode="contained"
          buttonColor={theme.colors.error}
          textColor={theme.colors.onError}
          onPress={() => setConfirming(true)}
          loading={submitting}
          // The password is the backend's requirement; disabling without it
          // saves a round trip that can only fail.
          disabled={submitting || !password}
        >
          {t('deleteAccount')}
        </Button>
        <Button mode="text" onPress={() => router.back()} disabled={submitting}>
          {t('cancel')}
        </Button>
      </View>

      {/* A second, explicit confirmation. The first button is destructive and
          red; this is the one that actually does it, and it names the
          consequence rather than asking "are you sure?". */}
      <Portal>
        <Dialog visible={confirming} onDismiss={() => setConfirming(false)}>
          <Dialog.Title>{t('deleteAccountConfirmTitle')}</Dialog.Title>
          <Dialog.Content>
            <Text>{t('deleteAccountConfirmBody')}</Text>
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setConfirming(false)}>{t('cancel')}</Button>
            <Button onPress={deleteAccount} textColor={theme.colors.error}>
              {t('deleteAccountConfirmAction')}
            </Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </Screen>
  );
}
