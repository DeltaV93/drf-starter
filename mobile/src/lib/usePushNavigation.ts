/**
 * Opening the right screen when someone taps a notification.
 *
 * Registering for push and then ignoring what arrives is half a feature: the
 * notification shows, the person taps it, and the app opens on whatever screen
 * it was last on. This is the other half.
 *
 * `useLastNotificationResponse` rather than an event listener, and the
 * difference matters. A listener only fires for taps that happen while the app
 * is running — but the common case is an app that was *not* running: the tap
 * is what launched it, and the response was delivered before any listener
 * could exist. This hook replays that one, so a cold start and a warm tap take
 * the same path.
 *
 * The destination goes through `safeRedirect` for the same reason the sign-in
 * one does. A push payload is not user input, but it is not this app's code
 * either — it is whatever the server, or anyone who can reach the push
 * service with your credentials, put in the `data` field.
 */

import * as Notifications from 'expo-notifications';
import { useRouter } from 'expo-router';
import { useEffect, useRef } from 'react';

import type { PushPayload } from './push';
import { safeRedirect } from './redirect';

export function usePushNavigation(): void {
  const router = useRouter();
  const response = Notifications.useLastNotificationResponse();

  // The hook keeps returning the same response on every render, so without
  // this the effect would navigate again on each one -- and would fight the
  // user's own navigation for as long as the app stayed open.
  const handled = useRef<string | null>(null);

  useEffect(() => {
    if (!response) return;

    const id = response.notification.request.identifier;
    if (handled.current === id) return;
    handled.current = id;

    const data = response.notification.request.content.data as PushPayload | undefined;
    if (!data?.path) return;

    // `push`, not `replace`: someone who taps a notification and then goes
    // back should end up where they were, not on a dead end.
    router.push(safeRedirect(data.path));
  }, [response, router]);
}
