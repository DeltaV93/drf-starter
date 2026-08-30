/**
 * Everything that is not a destination in its own right.
 *
 * The website spreads these across a header nav; a phone gets one list. The
 * rows follow the same flags the backend uses, so a row never leads to a
 * screen that can only 404.
 */

import { useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';
import { Button, Divider, List, SegmentedButtons, Text, useTheme } from 'react-native-paper';

import { Screen, ScreenHeader } from '../../components/Screen';
import { flags } from '../../lib/config';
import { unregisterFromPush } from '../../lib/push';
import { useAuth } from '../../store/auth';
import { useOrganizations } from '../../store/organization';
import { useToast } from '../../store/toast';
import { useColorSchemePreference } from '../../theme/colorScheme';
import type { AppTheme } from '../../theme/paper';

export default function SettingsScreen() {
  const theme = useTheme<AppTheme>();
  const router = useRouter();
  const { t } = useTranslation();
  const { logout } = useAuth();
  const { forget } = useOrganizations();
  const { preference, choose } = useColorSchemePreference();
  const toast = useToast();

  async function signOut() {
    // Unregister first, while the token still authenticates the call. Doing
    // it afterwards would be a request with no credential, and the device
    // would keep receiving this account's notifications.
    if (flags.push) await unregisterFromPush();
    await forget();
    await logout();
    toast.success(t('loggedOut'));
    router.replace('/login');
  }

  return (
    <Screen>
      <ScreenHeader title={t('settings')} />

      <Text variant="titleMedium">{t('themeLabel')}</Text>
      <SegmentedButtons
        value={preference}
        onValueChange={(value) => choose(value as typeof preference)}
        style={{ marginTop: theme.spacing(1), marginBottom: theme.spacing(3) }}
        buttons={[
          { value: 'system', label: t('themeSystem') },
          { value: 'light', label: t('themeLight') },
          { value: 'dark', label: t('themeDark') },
        ]}
      />

      <Text variant="titleMedium">{t('account')}</Text>
      <Divider style={{ marginVertical: theme.spacing(1) }} />

      <List.Item
        title={t('security')}
        description={t('securityRowHelp')}
        left={(props) => <List.Icon {...props} icon="shield-outline" />}
        onPress={() => router.push('/security')}
      />

      {flags.billing ? (
        <List.Item
          title={t('subscription')}
          description={t('subscriptionRowHelp')}
          left={(props) => <List.Icon {...props} icon="credit-card-outline" />}
          onPress={() => router.push('/subscription')}
        />
      ) : null}

      {flags.mcpClient ? (
        <List.Item
          title={t('connections')}
          description={t('connectionsRowHelp')}
          left={(props) => <List.Icon {...props} icon="power-plug-outline" />}
          onPress={() => router.push('/connections')}
        />
      ) : null}

      {/* Apple requires an app that creates accounts to delete them in the
          app, so this is a row here rather than a link to the website. It sits
          below sign-out because that is the one people actually want. */}
      <List.Item
        title={t('deleteAccount')}
        description={t('deleteAccountRowHelp')}
        titleStyle={{ color: theme.colors.error }}
        left={(props) => (
          <List.Icon {...props} icon="account-remove-outline" color={theme.colors.error} />
        )}
        onPress={() => router.push('/delete-account')}
      />

      <View style={{ marginTop: theme.spacing(4) }}>
        <Button mode="outlined" onPress={signOut} textColor={theme.colors.error}>
          {t('logout')}
        </Button>
      </View>
    </Screen>
  );
}
