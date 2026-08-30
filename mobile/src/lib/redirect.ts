/**
 * Where to send someone once they have signed in.
 *
 * The sign-in and sign-up screens take a `redirect` parameter so a flow that
 * had to detour through them can resume. The invitation screen is the reason
 * it exists: its URL carries the only copy of the invitation token, and
 * `replace('/profile')` after sign-in destroys the stack and the token with
 * it -- so the primary flow (open the emailed invite, sign in, join the team)
 * ended on the profile screen having joined nothing.
 *
 * ## Why the value is validated
 *
 * That parameter reaches the app from outside. Anyone can send someone a
 * `drfstarter://login?redirect=...` link, or an https one once the domain is
 * associated. An unchecked value is the mobile shape of an open redirect:
 * `//evil.example.com` and `https://evil.example.com` are both things
 * expo-router will happily navigate to, and the second one leaves the app
 * entirely -- which is exactly the trick a credible phishing page needs, since
 * the person arrived by signing in to the real app a moment earlier.
 *
 * So only an in-app absolute path is allowed through, and anything else falls
 * back rather than erroring: a stale or malformed link should still sign
 * someone in, just to the default place.
 */

import { appRoutes } from '@app/shared/routes';

export const DEFAULT_DESTINATION = appRoutes.profile;

export function safeRedirect(
  raw: string | string[] | undefined,
  fallback: string = DEFAULT_DESTINATION,
): string {
  // expo-router hands back an array when a parameter appears more than once.
  // Taking the first is arbitrary but harmless; both are validated anyway.
  const value = Array.isArray(raw) ? raw[0] : raw;

  if (!value) return fallback;

  // One leading slash, and nothing that could name a host or a scheme.
  // `//host` is protocol-relative and `https://host` is absolute; both leave
  // the app. A backslash is here because some parsers treat it as a slash.
  if (!value.startsWith('/')) return fallback;
  if (value.startsWith('//') || value.startsWith('/\\')) return fallback;
  if (value.includes('://')) return fallback;

  return value;
}
