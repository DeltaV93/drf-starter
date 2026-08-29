/**
 * Asking for a push token, and telling the backend about it.
 *
 * This is the client half of `apps/push/`. Neither half sends a notification:
 * which push service a project uses is not a decision a template should make,
 * and Expo's own service is one option among several.
 *
 * Everything here is best-effort. Registration is a background nicety, and a
 * failure -- permission refused, no network, the emulator having no push
 * support at all -- must never stop someone using the app. So the functions
 * below report what happened and never throw.
 */

import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

import { apiCall } from './api';
import { flags } from './config';
import { routes } from './routes';

export type RegistrationOutcome =
  | { status: 'registered'; token: string }
  | { status: 'skipped'; reason: string };

function platformName(): 'ios' | 'android' | 'web' {
  if (Platform.OS === 'ios') return 'ios';
  if (Platform.OS === 'android') return 'android';
  return 'web';
}

/**
 * Ask for permission and register this installation.
 *
 * Call it after sign-in rather than at launch. The permission prompt is a
 * one-shot: someone who declines it on the very first screen, before they have
 * any idea what the app is, cannot be asked again from inside the app -- they
 * have to find it in system settings. Asking once they have an account is the
 * difference between a considered yes and a reflexive no.
 */
export async function registerForPush(): Promise<RegistrationOutcome> {
  if (!flags.push) {
    return { status: 'skipped', reason: 'Push notifications are switched off.' };
  }

  // A simulator has no push service to register with, and asking produces an
  // error rather than a token.
  if (!Device.isDevice) {
    return { status: 'skipped', reason: 'Push needs a physical device.' };
  }

  try {
    const existing = await Notifications.getPermissionsAsync();
    let granted = existing.granted;

    if (!granted && existing.canAskAgain) {
      granted = (await Notifications.requestPermissionsAsync()).granted;
    }

    if (!granted) {
      return { status: 'skipped', reason: 'Notification permission was not granted.' };
    }

    const { data: token } = await Notifications.getExpoPushTokenAsync();

    await apiCall({
      url: routes.api.push.devices(),
      method: 'POST',
      data: {
        token,
        platform: platformName(),
        device_name: Device.deviceName ?? '',
      },
      errorMessage: 'Could not register for notifications.',
    });

    return { status: 'registered', token };
  } catch (error) {
    return {
      status: 'skipped',
      reason: error instanceof Error ? error.message : 'Could not register for notifications.',
    };
  }
}

/**
 * Stop this installation receiving notifications.
 *
 * Called on sign-out, and the reason it matters is shared devices: a token
 * left registered keeps delivering the previous user's notifications to a
 * phone that now belongs to someone else's session. The backend also moves a
 * token to whoever registers it next, but that only helps if there *is* a
 * next -- signing out and stopping there has to be safe on its own.
 */
export async function unregisterFromPush(): Promise<void> {
  if (!flags.push) return;

  try {
    const { data: token } = await Notifications.getExpoPushTokenAsync();
    await apiCall({ url: routes.api.push.device(token), method: 'DELETE' });
  } catch {
    // Sign-out must not fail because a device could not be unregistered. The
    // tokens are cleared regardless, so nothing this app holds still works.
  }
}
