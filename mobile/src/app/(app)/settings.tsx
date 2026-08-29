/**
 * Everything that is not a destination in its own right.
 *
 * The website spreads these across a header nav; a phone gets one list. The
 * rows follow the same flags the backend uses, so a row never leads to a
 * screen that can only 404.
 */

import { useRouter } from 'expo-router';
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
    toast.success('Signed out.');
    router.replace('/login');
  }

  return (
    <Screen>
      <ScreenHeader title="Settings" />

      <Text variant="titleMedium">Appearance</Text>
      <SegmentedButtons
        value={preference}
        onValueChange={(value) => choose(value as typeof preference)}
        style={{ marginTop: theme.spacing(1), marginBottom: theme.spacing(3) }}
        buttons={[
          { value: 'system', label: 'System' },
          { value: 'light', label: 'Light' },
          { value: 'dark', label: 'Dark' },
        ]}
      />

      <Text variant="titleMedium">Account</Text>
      <Divider style={{ marginVertical: theme.spacing(1) }} />

      <List.Item
        title="Security"
        description="Two-step verification, API keys, activity and your data"
        left={(props) => <List.Icon {...props} icon="shield-outline" />}
        onPress={() => router.push('/security')}
      />

      {flags.billing ? (
        <List.Item
          title="Subscription"
          description="Your current plan"
          left={(props) => <List.Icon {...props} icon="credit-card-outline" />}
          onPress={() => router.push('/subscription')}
        />
      ) : null}

      {flags.mcpClient ? (
        <List.Item
          title="Connections"
          description="Servers this account has connected"
          left={(props) => <List.Icon {...props} icon="power-plug-outline" />}
          onPress={() => router.push('/connections')}
        />
      ) : null}

      <View style={{ marginTop: theme.spacing(4) }}>
        <Button mode="outlined" onPress={signOut} textColor={theme.colors.error}>
          Sign out
        </Button>
      </View>
    </Screen>
  );
}
