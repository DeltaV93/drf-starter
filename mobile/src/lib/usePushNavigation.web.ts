/**
 * The web build has no notifications to navigate from.
 *
 * Metro picks this file over `usePushNavigation.ts` for the web target, which
 * is the idiomatic way to say "not on this platform" -- and the only way that
 * works, because the alternative is a conditional hook call.
 *
 * This is not hypothetical tidiness. `Notifications.useLastNotificationResponse`
 * is backed by a native module, and calling it on web throws:
 *
 *     ExpoNotifications.getLastNotificationResponse is not available on web
 *
 * The hook is mounted in the root layout, so that exception propagates out of
 * the very first render and the app shows a blank page. Nothing else fails
 * first, and no test caught it -- the app was only ever bundled, never run.
 */

export function usePushNavigation(): void {
  // Deliberately empty.
}
