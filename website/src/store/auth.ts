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
import type { AuthPayload, User } from '../lib/types';

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous';

export const userAtom = atom<User | null>(null);
export const authStatusAtom = atom<AuthStatus>('loading');

export const isAuthenticatedAtom = atom((get) => get(authStatusAtom) === 'authenticated');
export const isAuthLoadingAtom = atom((get) => get(authStatusAtom) === 'loading');

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
    async (credentials: LoginCredentials): Promise<User> => {
      const envelope = await apiCall<AuthPayload>({
        url: routes.api.auth.login(),
        method: 'POST',
        data: credentials,
        errorMessage: 'Could not sign you in.',
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
