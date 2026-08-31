/**
 * Fetching over-the-air updates without ever interrupting anyone.
 *
 * The rule this file exists to hold: an update is downloaded in the
 * background and takes effect the *next* time the app is launched from cold.
 * Nothing here calls `Updates.reloadAsync()`. Reloading is the tempting call
 * -- the fix reaches people sooner -- but it restarts the app underneath
 * whoever is using it, losing whatever they had typed, for a change they did
 * not ask for and cannot decline. Once fetched, expo-updates applies the new
 * bundle on the next cold start by itself; the work here is only deciding
 * when to look.
 *
 * Two moments are worth looking at, and launch is not enough on its own: a
 * phone that is never fully closed can run the same JavaScript for weeks, so
 * the app also checks when it comes back to the foreground.
 *
 * Everything is guarded and every failure is swallowed. `Updates.isEnabled` is
 * false in Expo Go, in a development build, and in any build made without an
 * EAS project configured -- which is every checkout of this template until
 * somebody runs `eas init`. An update check is the last thing that should be
 * able to stop an app starting.
 */

import * as Updates from 'expo-updates';
import { useEffect } from 'react';
import { AppState, type AppStateStatus, Platform } from 'react-native';

/** Don't ask again within this window, however often the app is foregrounded. */
const MINIMUM_INTERVAL_MS = 30 * 60 * 1000;

let lastCheckedAt = 0;

/** Exported for the tests; nothing else should need to reach in here. */
export function resetUpdateThrottle() {
  lastCheckedAt = 0;
}

/**
 * Look for an update and download it, or do nothing at all.
 *
 * Resolves either way. The caller has nothing to do with the answer -- the
 * downloaded bundle is picked up on the next cold start whether or not
 * anything here reports back.
 */
export async function fetchUpdateInBackground(): Promise<boolean> {
  // Web has no native runtime to update, and calling into the module there is
  // how `usePushNavigation` once took the whole app down.
  if (Platform.OS === 'web' || !Updates.isEnabled) return false;

  const now = Date.now();
  if (now - lastCheckedAt < MINIMUM_INTERVAL_MS) return false;
  lastCheckedAt = now;

  try {
    const { isAvailable } = await Updates.checkForUpdateAsync();
    if (!isAvailable) return false;
    await Updates.fetchUpdateAsync();
    return true;
  } catch {
    // Offline, a captive portal, an update server having a bad day. None of
    // it is the user's problem, and there is nothing useful to say about it:
    // the app carries on with the bundle it already has, which works.
    return false;
  }
}

/**
 * Check on launch, and again whenever the app returns to the foreground.
 *
 * No state, and deliberately: there is nothing to render. A hook that stored
 * "an update is ready" would only tempt the next person into showing a dialog
 * about it.
 */
export function useBackgroundUpdates() {
  useEffect(() => {
    // Not awaited: the app must not wait on the network to become usable.
    void fetchUpdateInBackground();

    const onChange = (state: AppStateStatus) => {
      if (state === 'active') void fetchUpdateInBackground();
    };

    const subscription = AppState.addEventListener('change', onChange);
    return () => subscription.remove();
  }, []);
}
