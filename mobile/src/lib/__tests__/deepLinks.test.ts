/**
 * That an emailed link still opens the screen it names.
 *
 * Three things have to agree, and none of them import each other: the shared
 * route table, the backend's published association documents, and the
 * filenames expo-router derives its linking map from. Rename any one and
 * nothing breaks at build time -- the link opens the app, the router finds no
 * route, and the user gets the home screen with no explanation.
 *
 * These assertions are cheap and they are the only thing standing between
 * that rename and a verification email that silently stops working.
 */

import { existsSync } from 'fs';
import { join } from 'path';

import { appRoutes } from '@app/shared/routes';

import { CLAIMED_ROUTES, associationPatternFor, routeFileFor } from '../deepLinks';

const APP_DIR = join(__dirname, '..', '..', 'app');

/**
 * The backend's default MOBILE_DEEP_LINK_PATHS, restated.
 *
 * Restated rather than imported, because it lives in Python. A change on
 * either side has to be made on both, and this is what says so out loud --
 * see `template/settings/base.py` and `docs/configuration.md`.
 */
const BACKEND_DEFAULT_PATHS = ['/verify-email/*', '/confirm-password/*', '/invitations/*'];

describe('the claimed routes', () => {
  it('are the ones the backend emails', () => {
    expect(CLAIMED_ROUTES).toEqual([
      appRoutes.verifyEmail(),
      appRoutes.confirmPassword(),
      appRoutes.acceptInvitation(),
    ]);
  });

  it('each have a route file to land on', () => {
    for (const path of CLAIMED_ROUTES) {
      const file = join(APP_DIR, routeFileFor(path));
      expect({ path, exists: existsSync(file) }).toEqual({ path, exists: true });
    }
  });

  it('produce the association patterns the backend publishes', () => {
    // A pattern naming the parameters would match nothing: the platforms
    // match on prefix, so `/verify-email/:uid/:token` has to be published as
    // `/verify-email/*`.
    expect(CLAIMED_ROUTES.map(associationPatternFor)).toEqual(BACKEND_DEFAULT_PATHS);
  });
});

describe('the path-to-filename mapping', () => {
  it('turns route parameters into expo-router segments', () => {
    expect(routeFileFor('/verify-email/:uid/:token')).toBe('verify-email/[uid]/[token].tsx');
    expect(routeFileFor('/invitations/:token')).toBe('invitations/[token].tsx');
  });
});

describe('the sign-in routes', () => {
  it('exist under the names the app navigates to', () => {
    // `router.replace('/login')` is a string, so a renamed file is a runtime
    // no-op rather than a type error.
    for (const path of [appRoutes.login, appRoutes.signup, appRoutes.passwordReset]) {
      const file = join(APP_DIR, `${path.replace(/^\//, '')}.tsx`);
      expect({ path, exists: existsSync(file) }).toEqual({ path, exists: true });
    }
  });

  it('has the signed-in screens inside the protected group', () => {
    for (const path of [appRoutes.profile, appRoutes.organization, appRoutes.security]) {
      const file = join(APP_DIR, '(app)', `${path.replace(/^\//, '')}.tsx`);
      expect({ path, exists: existsSync(file) }).toEqual({ path, exists: true });
    }
  });
});
