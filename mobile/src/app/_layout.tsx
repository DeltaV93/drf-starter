/**
 * The root of the app: providers, the one-time bootstraps, and the gate.
 *
 * expo-router renders this above every route, so it is the only place that
 * runs exactly once per launch -- which is what the bootstraps need.
 */

import * as Linking from 'expo-linking';
import { Stack, useRouter, useSegments } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Banner, PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { PaperIcon } from '../components/PaperIcon';
import { Toast } from '../components/Toast';
import { UpgradeRequired } from '../components/UpgradeRequired';
import '../i18n';
import { initialiseMonitoring, withMonitoring } from '../lib/monitoring';
import { useBackgroundUpdates } from '../lib/updates';
import { usePushNavigation } from '../lib/usePushNavigation';
import { useUpgradeGate } from '../lib/useUpgradeGate';
import { useAuthBootstrap } from '../store/auth';
import { useOrganizationBootstrap } from '../store/organization';
import {
  useAppTheme,
  useColorSchemeBootstrap,
  useColorSchemeHydrated,
  useResolvedColorScheme,
} from '../theme/colorScheme';

// Before anything renders, so a crash during the first paint is reported
// rather than lost. A no-op when no DSN is configured.
initialiseMonitoring();

// Hold the splash until we know who is signed in.
//
// The keychain read is asynchronous, so the first frame always looks
// anonymous. Left to hide itself, the splash goes as soon as that frame
// paints -- and a returning user sees the signed-out home screen flash past
// before landing on their profile. The website has the same problem and
// solves it the same way, with the inline script in index.html.
//
// Failure is ignored on purpose: on a platform with no splash module this
// rejects, and an app that will not start because it could not keep a splash
// screen up is a worse outcome than a flash.
SplashScreen.preventAutoHideAsync().catch(() => {});

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

function RootLayout() {
  const status = useAuthBootstrap();
  useColorSchemeBootstrap();
  useOrganizationBootstrap();
  useSessionGate(status);
  // Unconditional: hooks cannot be called behind a flag, and the hook itself
  // does nothing when no notification has been tapped -- which is every
  // launch on a deployment with push switched off.
  usePushNavigation();
  // Downloads in the background and takes effect on the next cold start.
  // Nothing to render, and nothing to wait for.
  useBackgroundUpdates();

  const gate = useUpgradeGate();
  // Once per launch: this component mounts once, so declining here is
  // remembered for the session and forgotten by the next one. Deliberately
  // not persisted -- a nudge someone dismissed in March should come back.
  const [nudgeDismissed, setNudgeDismissed] = useState(false);

  const theme = useAppTheme();
  const scheme = useResolvedColorScheme();
  const { t } = useTranslation();
  const colorSchemeReady = useColorSchemeHydrated();

  // Three answers are needed before the first visible frame: who is signed
  // in decides the screen, the stored theme decides its colours, and the
  // version check decides whether there is an app to show at all. Hiding on
  // fewer trades a flash of the wrong screen for a flash of the wrong
  // palette -- or, worse, a blocked build showing its home screen for a beat
  // before the wall drops.
  const ready = status !== 'loading' && colorSchemeReady && !gate.pending;

  useEffect(() => {
    if (ready) SplashScreen.hideAsync().catch(() => {});
  }, [ready]);

  // Rendered in place of the navigator, not above it. A wall you can
  // navigate behind is not a wall -- and this stays inside the providers so
  // it is themed and translated like everything else.
  if (gate.check?.requirement === 'required') {
    return (
      <SafeAreaProvider>
        <PaperProvider theme={theme} settings={{ icon: PaperIcon }}>
          <StatusBar style={scheme === 'dark' ? 'light' : 'dark'} />
          <UpgradeRequired check={gate.check} />
        </PaperProvider>
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <PaperProvider theme={theme} settings={{ icon: PaperIcon }}>
        {/* Inverted on purpose: the status bar text has to contrast with the
            app's background, so a dark theme needs light text. */}
        <StatusBar style={scheme === 'dark' ? 'light' : 'dark'} />
        {gate.check?.requirement === 'recommended' && !nudgeDismissed ? (
          <Banner
            visible
            actions={[
              {
                label: t('upgradeAction'),
                onPress: () => {
                  if (gate.check?.store_url) void Linking.openURL(gate.check.store_url);
                  setNudgeDismissed(true);
                },
              },
              { label: t('upgradeLater'), onPress: () => setNudgeDismissed(true) },
            ]}
          >
            {gate.check.message || t('upgradeAvailableTitle')}
          </Banner>
        ) : null}
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: theme.colors.surface },
            headerTintColor: theme.colors.onSurface,
            contentStyle: { backgroundColor: theme.colors.background },
          }}
        >
          <Stack.Screen name="index" options={{ headerShown: false }} />
          <Stack.Screen name="(app)" options={{ headerShown: false }} />
          <Stack.Screen name="login" options={{ title: t('login') }} />
          <Stack.Screen name="signup" options={{ title: t('createAccount') }} />
          <Stack.Screen name="two-factor" options={{ title: t('twoStepTitle') }} />
          <Stack.Screen name="reset-password" options={{ title: t('resetPassword') }} />
        </Stack>
        <Toast />
      </PaperProvider>
    </SafeAreaProvider>
  );
}

// Wrapped so an unhandled render error anywhere in the tree is reported
// instead of showing a blank screen. Identity function when monitoring is off.
export default withMonitoring(RootLayout);
