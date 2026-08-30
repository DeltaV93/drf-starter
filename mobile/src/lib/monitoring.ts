/**
 * Crash reporting, mirroring the backend's.
 *
 * The backend has reported its 500s to Sentry since before this app existed.
 * A crash on someone's phone had nowhere to go at all -- no log to read, no
 * dashboard, and the person it happened to is the last to tell you.
 *
 * Deliberately the same shape of decision as `template/settings/base.py`:
 * off unless a DSN is configured, never during a test run, and personal
 * information off by default. That last one is a decision rather than a
 * default: turning it on ships usernames, email addresses and IP addresses to
 * a third party, which is something to document rather than inherit.
 */

import * as Sentry from '@sentry/react-native';

/**
 * A DSN is not a secret -- it is designed to ship inside a client -- so it
 * lives with the other `EXPO_PUBLIC_` values rather than in a build secret.
 * Absent, nothing here initialises and nothing is sent.
 */
const DSN = process.env.EXPO_PUBLIC_SENTRY_DSN ?? '';

const SEND_PII = process.env.EXPO_PUBLIC_SENTRY_SEND_PII === 'true';

/** What `__DEV__` means for reporting: a crash on your own machine. */
const IS_DEVELOPMENT = typeof __DEV__ !== 'undefined' && __DEV__;

export function initialiseMonitoring(): void {
  // No DSN, or a test run: a CI machine with a DSN in its environment would
  // otherwise fill a real project with noise from deliberately-failing tests.
  if (!DSN || process.env.NODE_ENV === 'test') return;

  Sentry.init({
    dsn: DSN,
    environment: IS_DEVELOPMENT ? 'development' : 'production',
    // Off by default, for the reason the backend records: this ships people's
    // identities to a third party. EXPO_PUBLIC_SENTRY_SEND_PII turns it on
    // once someone has decided that is acceptable and said so in a privacy
    // notice.
    sendDefaultPii: SEND_PII,
    // Sampled at zero by default. Performance tracing on a mobile client is
    // a per-session cost in battery and bandwidth that a template should not
    // spend on a project's behalf.
    tracesSampleRate: Number(process.env.EXPO_PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? '0'),
    // Reporting a crash from a build nobody can identify wastes the report.
    // EAS sets this; locally it is simply absent.
    release: process.env.EXPO_PUBLIC_SENTRY_RELEASE || undefined,
  });
}

/**
 * Wrap the root component so an unhandled render error is reported rather
 * than just showing a blank screen.
 *
 * A no-op when monitoring is off, so the tree is identical either way.
 */
export const withMonitoring: typeof Sentry.wrap = (component) =>
  DSN ? Sentry.wrap(component) : component;
