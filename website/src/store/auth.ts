/**
 * Authentication state.
 *
 * The server session is the source of truth, not localStorage. On boot the
 * app asks /users/me/ who it is talking to; a stale client-side flag can
 * never grant access to a session the server has already dropped.
 */

import { atom, useAtom, useAtomValue, useSetAtom } from 'jotai';
import { useCallback, useEffect } from 'react';

import { apiCall, ensureCsrfToken } from '../lib/api';
import { routes } from '../lib/routes';
import type { AuthPayload, User } from '@app/shared/types';

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous';

export const userAtom = atom<User | null>(null);
export const authStatusAtom = atom<AuthStatus>('loading');

export const isAuthenticatedAtom = atom((get) => get(authStatusAtom) === 'authenticated');
export const isAuthLoadingAtom = atom((get) => get(authStatusAtom) === 'loading');

/**
 * What a login attempt produced.
 *
 * With two-factor enrolled the password step does NOT establish a session --
 * the backend answers `twoFactorRequired` and waits. Reading `data.user`
 * unconditionally (as this did) set the user to undefined while marking the
 * store authenticated, which is worse than failing.
 */
export type LoginResult =
  | { status: 'authenticated'; user: User }
  | { status: 'two-factor-required' };

export interface LoginCredentials {
  /** An email address, or a username for an account that has one. */
  identifier: string;
  password: string;
}

export interface RegistrationDetails {
  /** Optional -- send '' and the account simply has no handle. */
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  password2: string;
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
      // A 401/403 here is the normal answer for a visitor, not an error.
      setUser(null);
      setStatus('anonymous');
      return null;
    }
  }, [setUser, setStatus]);

  const login = useCallback(
    async (credentials: LoginCredentials): Promise<LoginResult> => {
      const envelope = await apiCall<AuthPayload & { twoFactorRequired?: boolean }>({
        url: routes.api.auth.login(),
        method: 'POST',
        data: credentials,
        errorMessage: 'Could not sign you in.',
      });

      if (envelope.data?.twoFactorRequired) {
        // No session yet, and no user in the payload. The pending state lives
        // in the session cookie; the caller collects a code and verifies.
        return { status: 'two-factor-required' };
      }

      const nextUser = envelope.data!.user;
      setUser(nextUser);
      setStatus('authenticated');
      return { status: 'authenticated', user: nextUser };
    },
    [setUser, setStatus],
  );

  /** Finish a login that stopped for the second factor. */
  const verifyTwoFactor = useCallback(
    async (code: string): Promise<User> => {
      const envelope = await apiCall<AuthPayload>({
        url: routes.api.auth.twoFactor.verify(),
        method: 'POST',
        data: { code },
        errorMessage: 'That code was not accepted.',
      });

      const nextUser = envelope.data!.user;
      setUser(nextUser);
      setStatus('authenticated');
      return nextUser;
    },
    [setUser, setStatus],
  );

  const register = useCallback(
    async (details: RegistrationDetails): Promise<User> => {
      const envelope = await apiCall<AuthPayload>({
        url: routes.api.auth.register(),
        method: 'POST',
        data: details,
        errorMessage: 'Could not create your account.',
      });

      const nextUser = envelope.data!.user;
      setUser(nextUser);
      setStatus('authenticated');
      return nextUser;
    },
    [setUser, setStatus],
  );

  const logout = useCallback(async (): Promise<void> => {
    try {
      await apiCall({ url: routes.api.auth.logout(), method: 'POST' });
    } finally {
      // Clear locally even if the call failed -- the user asked to sign out.
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
export function useAuthBootstrap() {
  const setUser = useSetAtom(userAtom);
  const setStatus = useSetAtom(authStatusAtom);
  const status = useAtomValue(authStatusAtom);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      // Prime the CSRF cookie so the first form submission does not have to
      // make an extra round trip.
      await ensureCsrfToken();

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

  return status;
}
