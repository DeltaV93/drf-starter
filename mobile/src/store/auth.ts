/**
 * Authentication state.
 *
 * The server is the source of truth, as on the website -- but "who am I"
 * cannot be answered without first asking, and on a phone that answer is
 * wanted before the first screen paints. So the bootstrap reads the stored
 * token pair, then confirms it against `/users/me/`. A token that the backend
 * no longer honours must never be enough to render a signed-in screen.
 *
 * The store also listens for the client giving up on a refresh, which is the
 * one way a session ends without anyone tapping anything.
 */

import { atom, useAtom, useAtomValue, useSetAtom } from 'jotai';
import { useCallback, useEffect } from 'react';

import type { TokenResponse, User } from '@app/shared/types';
import { isTokenChallenge } from '@app/shared/types';

import { apiCall, onSessionEnded } from '../lib/api';
import { routes } from '../lib/routes';
import { clearTokens, currentTokens, loadTokens, saveTokens } from '../lib/tokenStore';

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous';

export const userAtom = atom<User | null>(null);
export const authStatusAtom = atom<AuthStatus>('loading');

export const isAuthenticatedAtom = atom((get) => get(authStatusAtom) === 'authenticated');
export const isAuthLoadingAtom = atom((get) => get(authStatusAtom) === 'loading');

/**
 * What a sign-in attempt produced.
 *
 * With two-factor enrolled the password step issues no tokens -- the backend
 * answers with a challenge and waits. Reading `access` unconditionally would
 * store `undefined` and mark the app signed in, which is worse than failing.
 */
export type LoginResult =
  | { status: 'authenticated'; user: User }
  | { status: 'two-factor-required'; challenge: string };

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegistrationDetails {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  password2: string;
}

async function storePair(response: TokenResponse) {
  if (isTokenChallenge(response)) return;
  await saveTokens({ access: response.access, refresh: response.refresh });
}

export function useAuth() {
  const [user, setUser] = useAtom(userAtom);
  const [status, setStatus] = useAtom(authStatusAtom);

  const refresh = useCallback(async (): Promise<User | null> => {
    try {
      const envelope = await apiCall<User>({ url: routes.api.users.me(), method: 'GET' });
      const nextUser = envelope.data ?? null;
      setUser(nextUser);
      setStatus(nextUser ? 'authenticated' : 'anonymous');
      return nextUser;
    } catch {
      setUser(null);
      setStatus('anonymous');
      return null;
    }
  }, [setUser, setStatus]);

  const login = useCallback(
    async (credentials: LoginCredentials): Promise<LoginResult> => {
      const envelope = await apiCall<TokenResponse>({
        url: routes.api.auth.token.obtain(),
        method: 'POST',
        data: credentials,
        errorMessage: 'Could not sign you in.',
      });

      const payload = envelope.data!;
      if (isTokenChallenge(payload)) {
        return { status: 'two-factor-required', challenge: payload.challenge };
      }

      await storePair(payload);
      setUser(payload.user);
      setStatus('authenticated');
      return { status: 'authenticated', user: payload.user };
    },
    [setUser, setStatus],
  );

  /** Finish a sign-in that stopped for the second factor. */
  const verifyTwoFactor = useCallback(
    async (challenge: string, code: string): Promise<User> => {
      const envelope = await apiCall<TokenResponse>({
        url: routes.api.auth.token.verifyTwoFactor(),
        method: 'POST',
        data: { challenge, code },
        errorMessage: 'That code was not accepted.',
      });

      const payload = envelope.data!;
      if (isTokenChallenge(payload)) {
        // The backend does not do this, and if it ever did, silently
        // returning would leave the caller on a spinner forever.
        throw new Error('Verification did not complete.');
      }

      await storePair(payload);
      setUser(payload.user);
      setStatus('authenticated');
      return payload.user;
    },
    [setUser, setStatus],
  );

  /**
   * Register, then sign in.
   *
   * Two calls rather than one. Registration establishes a *session* on the
   * backend, which is no use to a client that authenticates with a header --
   * so the tokens have to be asked for separately. Doing it here rather than
   * on the sign-up screen is what keeps "create an account" a single action
   * from the caller's point of view.
   */
  const register = useCallback(
    async (details: RegistrationDetails): Promise<User> => {
      await apiCall({
        url: routes.api.auth.register(),
        method: 'POST',
        data: details,
        errorMessage: 'Could not create your account.',
      });

      const result = await login({
        username: details.username,
        password: details.password,
      });

      if (result.status !== 'authenticated') {
        // A brand-new account cannot have a second factor enrolled, so this
        // is unreachable -- but returning `undefined` as a User if it ever
        // happened would fail somewhere far away from here.
        throw new Error('Account created, but signing in did not complete.');
      }
      return result.user;
    },
    [login],
  );

  const logout = useCallback(async (): Promise<void> => {
    const tokens = currentTokens();
    try {
      if (tokens) {
        await apiCall({
          url: routes.api.auth.token.revoke(),
          method: 'POST',
          data: { refresh: tokens.refresh },
        });
      }
    } catch {
      // The user asked to sign out. Whether the server agreed is not their
      // problem, and refusing would leave them signed in on a shared device.
    } finally {
      await clearTokens();
      setUser(null);
      setStatus('anonymous');
    }
  }, [setUser, setStatus]);

  return {
    user,
    status,
    isAuthenticated: status === 'authenticated',
    isLoading: status === 'loading',
    login,
    verifyTwoFactor,
    logout,
    register,
    refresh,
  };
}

/**
 * Resolve the session once, at startup. Mount this above the router.
 */
export function useAuthBootstrap(): AuthStatus {
  const setUser = useSetAtom(userAtom);
  const setStatus = useSetAtom(authStatusAtom);
  const status = useAtomValue(authStatusAtom);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      const tokens = await loadTokens();
      if (cancelled) return;

      if (!tokens) {
        setUser(null);
        setStatus('anonymous');
        return;
      }

      // Having a token is not the same as having a session. It may have been
      // revoked from another device, or the account deleted. Ask.
      try {
        const envelope = await apiCall<User>({ url: routes.api.users.me(), method: 'GET' });
        if (cancelled) return;
        setUser(envelope.data ?? null);
        setStatus(envelope.data ? 'authenticated' : 'anonymous');
      } catch {
        if (cancelled) return;
        setUser(null);
        setStatus('anonymous');
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [setUser, setStatus]);

  // The client clears the tokens when a refresh fails; this is what turns
  // that into a navigation. Without it the app keeps rendering signed-in
  // screens that 401 one by one.
  useEffect(
    () =>
      onSessionEnded(() => {
        setUser(null);
        setStatus('anonymous');
      }),
    [setUser, setStatus],
  );

  return status;
}
