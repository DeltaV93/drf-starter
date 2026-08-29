/**
 * Everything the app reads from its environment, in one place.
 *
 * Expo inlines only the `EXPO_PUBLIC_` prefix, and only where the whole name
 * is written out at the point of use. It is a build-time substitution, not a
 * lookup, so `process.env[someVariable]` is `undefined` in a release build
 * even though it works in the dev server -- which is why every name below is
 * spelled out rather than generated in a loop.
 *
 * `apps/core/tests/test_env_documented.py` scans this directory for those
 * reads and fails if one is missing from `mobile/.env.example` or from
 * `docs/configuration.md`.
 */

import { DEFAULT_API_BASE_URL } from '@app/shared/routes';

function flag(value: string | undefined): boolean {
  return value === 'true';
}

/**
 * Where the API lives.
 *
 * No same-origin default, unlike the website: a simulator is not the machine
 * Django is running on, and an Android emulator cannot reach `localhost` at
 * all -- it needs 10.0.2.2. A wrong value here looks like the backend being
 * down, so it is worth checking first.
 */
export const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;

/** Where web-only journeys continue -- billing, chiefly. */
export const WEB_URL = process.env.EXPO_PUBLIC_WEB_URL ?? '';

/**
 * Feature flags, each the twin of a backend one.
 *
 * Out of step, a screen renders and then 404s against the API -- exactly the
 * same failure the website has, for the same reason.
 */
export const flags = {
  billing: flag(process.env.EXPO_PUBLIC_STRIPE_ENABLED),
  organizations: flag(process.env.EXPO_PUBLIC_ORGANIZATIONS_ENABLED),
  twoFactor: flag(process.env.EXPO_PUBLIC_TWO_FACTOR_ENABLED),
  apiKeys: flag(process.env.EXPO_PUBLIC_API_KEYS_ENABLED),
  uploads: flag(process.env.EXPO_PUBLIC_UPLOADS_ENABLED),
  auditLog: flag(process.env.EXPO_PUBLIC_AUDIT_LOG_ENABLED),
  socialAuth: flag(process.env.EXPO_PUBLIC_SOCIAL_AUTH_ENABLED),
  mcpClient: flag(process.env.EXPO_PUBLIC_MCP_CLIENT_ENABLED),
  push: flag(process.env.EXPO_PUBLIC_PUSH_ENABLED),
} as const;
