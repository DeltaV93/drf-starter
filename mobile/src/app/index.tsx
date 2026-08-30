/**
 * The landing screen.
 *
 * Anonymous: what this is, and the two ways in. Signed in: straight through
 * to the app. The redirect lives here rather than in the root gate because
 * "already signed in" should not stop a deep link from opening the screen it
 * names -- see the note on `useSessionGate`.
 */

import { identity } from '@app/shared/brand';
import { Redirect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';
import { ActivityIndicator, Button, Text, useTheme } from 'react-native-paper';

import { Screen } from '../components/Screen';
import { useAuth } from '../store/auth';
import type { AppTheme } from '../theme/paper';

export default function HomeScreen() {
  const theme = useTheme<AppTheme>();
  const router = useRouter();
  const { t } = useTranslation();
  const { status } = useAuth();

  if (status === 'loading') {
    return (
      <Screen scrollable={false}>
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
          <ActivityIndicator accessibilityLabel={t('loading')} />
        </View>
      </Screen>
    );
  }

  if (status === 'authenticated') {
    return <Redirect href="/profile" />;
  }

  return (
    <Screen scrollable={false}>
      <View style={{ flex: 1, justifyContent: 'center', gap: theme.spacing(2) }}>
        <Text variant="displaySmall">{identity.name}</Text>
        <Text variant="bodyLarge" style={{ color: theme.colors.onSurfaceVariant }}>
          {identity.tagline}
        </Text>

        <View style={{ marginTop: theme.spacing(4), gap: theme.spacing(1.5) }}>
          <Button mode="contained" onPress={() => router.push('/login')}>
            {t('login')}
          </Button>
          <Button mode="outlined" onPress={() => router.push('/signup')}>
            {t('createAccount')}
          </Button>
        </View>
      </View>
    </Screen>
  );
}
