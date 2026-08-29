/**
 * The emailed links this app claims, and where each one lands.
 *
 * There is no router configuration here on purpose. expo-router derives its
 * linking map from the filenames under `src/app/`, so a universal link for
 * `/verify-email/<uid>/<token>` opens `app/verify-email/[uid]/[token].tsx`
 * with no wiring at all -- which is exactly why this file exists.
 *
 * Nothing *fails* when a filename stops matching. The link opens the app, the
 * router finds no route, and the user gets the home screen with no explanation
 * -- on a device, from an email, days after the rename that caused it. The
 * table below is what a test can compare against the shared route table and
 * against the files actually on disk, so that rename fails in CI instead.
 *
 * Three things have to agree for a link to work end to end:
 *
 *   1. `appRoutes` here                    -- and on the website
 *   2. `MOBILE_DEEP_LINK_PATHS` on the backend, which is published in
 *      `/.well-known/apple-app-site-association` and `assetlinks.json`
 *   3. the filenames under `src/app/`
 */

import { appRoutes } from '@app/shared/routes';

/**
 * Each claimed URL path, with the expo-router file that answers it.
 *
 * The `:param` segments come from the shared route table; the `[param]` ones
 * are expo-router's spelling of the same thing. Converting between them is
 * the whole mapping, and it is done here rather than by hand so a new
 * parameter cannot be added to one form and forgotten in the other.
 */
export const CLAIMED_ROUTES = [
  appRoutes.verifyEmail(),
  appRoutes.confirmPassword(),
  appRoutes.acceptInvitation(),
] as const;

/** `/verify-email/:uid/:token` -> `verify-email/[uid]/[token].tsx` */
export function routeFileFor(path: string): string {
  const segments = path
    .split('/')
    .filter(Boolean)
    .map((segment) => (segment.startsWith(':') ? `[${segment.slice(1)}]` : segment));
  return `${segments.join('/')}.tsx`;
}

/**
 * The pattern each claimed route becomes in an association document.
 *
 * `/verify-email/:uid/:token` is published as `/verify-email/*` -- the
 * platforms match on prefix, not on shape, and a pattern naming the
 * parameters would match nothing.
 */
export function associationPatternFor(path: string): string {
  const [, first] = path.split('/');
  return `/${first}/*`;
}
