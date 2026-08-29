/**
 * The root of the app: providers, the one-time bootstraps, and the gate.
 *
 * expo-router renders this above every route, so it is the only place that
 * runs exactly once per launch -- which is what the bootstraps need.
 */

import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { PaperIcon } from '../components/PaperIcon';
import { Toast } from '../components/Toast';
import '../i18n';
import { useAuthBootstrap } from '../store/auth';
import { useOrganizationBootstrap } from '../store/organization';
import { useAppTheme, useColorSchemeBootstrap, useResolvedColorScheme } from '../theme/colorScheme';

/** The route group that requires a session. Everything else is public. */
const PROTECTED_GROUP = '(app)';

/**
 * Send people where their session says they belong.
 *
 * Only ever *out* of the protected group, and only once the session has
 * resolved. Two rules, and both matter:
 *
 * Nothing redirects while `status` is 'loading'. A returning user's token is
 * read from the keychain asynchronously, so the first frame always looks
 * anonymous -- redirecting on it would bounce every returning user to the
 * sign-in screen and then back, on every launch.
 *
 * And an authenticated user is not force-marched into the app. Sign-in and
 * sign-up do their own navigation, and a redirect here as well would fight
 * them -- but a deep link into `/verify-email/...` has to keep working for
 * someone already signed in, which a blanket "authenticated ⇒ go to /profile"
 * would break.
 */
function useSessionGate(status: 'loading' | 'authenticated' | 'anonymous') {
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (status === 'loading') return;

    const inProtectedGroup = segments[0] === PROTECTED_GROUP;
    if (status === 'anonymous' && inProtectedGroup) {
      router.replace('/login');
    }
  }, [status, segments, router]);
}

export default function RootLayout() {
  const status = useAuthBootstrap();
  useColorSchemeBootstrap();
  useOrganizationBootstrap();
  useSessionGate(status);

  const theme = useAppTheme();
  const scheme = useResolvedColorScheme();

  return (
    <SafeAreaProvider>
      <PaperProvider theme={theme} settings={{ icon: PaperIcon }}>
        {/* Inverted on purpose: the status bar text has to contrast with the
            app's background, so a dark theme needs light text. */}
        <StatusBar style={scheme === 'dark' ? 'light' : 'dark'} />
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: theme.colors.surface },
            headerTintColor: theme.colors.onSurface,
            contentStyle: { backgroundColor: theme.colors.background },
          }}
        >
          <Stack.Screen name="index" options={{ headerShown: false }} />
          <Stack.Screen name="(app)" options={{ headerShown: false }} />
          <Stack.Screen name="login" options={{ title: 'Sign in' }} />
          <Stack.Screen name="signup" options={{ title: 'Create an account' }} />
          <Stack.Screen name="two-factor" options={{ title: 'Verification' }} />
          <Stack.Screen name="reset-password" options={{ title: 'Reset password' }} />
        </Stack>
        <Toast />
      </PaperProvider>
    </SafeAreaProvider>
  );
}
