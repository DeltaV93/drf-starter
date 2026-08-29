/**
 * The single HTTP client for the app.
 *
 * Bearer-token auth means two things have to be right on every request: the
 * access token has to be attached, and when it expires the whole thing has to
 * recover without the user noticing. Both are handled here so no screen has
 * to think about it.
 *
 * Everything downstream of the response -- unwrapping the envelope, turning a
 * failure into a field-addressable ApiError -- is in `@app/shared/api`, which
 * the website uses too. Only the part above that is mobile-specific.
 *
 * ## Why the refresh is single-flight
 *
 * An access token expires while the app is in the background, and the moment
 * it comes forward five screens fire their requests at once. Five 401s arrive
 * within milliseconds of each other. Refreshing per 401 would spend the
 * refresh token five times -- and rotation means the first spend invalidates
 * it, so four of those refreshes fail and the user is thrown back to the
 * sign-in screen for no reason they can see. So the first 401 starts the
 * refresh and everything else waits on the same promise.
 */

import axios, {
  type AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios';

import { createApiClient, toApiError } from '@app/shared/api';
import type { ApiEnvelope, TokenPair } from '@app/shared/types';

import { routes } from './routes';
import { clearTokens, currentTokens, saveTokens } from './tokenStore';

export { ApiError } from '@app/shared/api';

/** Marks a request that has already been retried once after a refresh. */
interface RetryableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

export const http: AxiosInstance = axios.create({
  headers: { 'Content-Type': 'application/json' },
  // Long enough to survive a slow mobile network, short enough that a screen
  // does not sit on a spinner for a minute when there is no signal at all.
  timeout: 20000,
});

// ---------------------------------------------------------------------------
// Being told the session ended
//
// The client cannot navigate -- it has no router and should not have one --
// but it is the only thing that knows a refresh has failed. So it publishes
// the fact and the auth store, which does know how to react, listens.
// ---------------------------------------------------------------------------

type SessionEndedListener = () => void;

const sessionEndedListeners = new Set<SessionEndedListener>();

export function onSessionEnded(listener: SessionEndedListener): () => void {
  sessionEndedListeners.add(listener);
  return () => sessionEndedListeners.delete(listener);
}

function announceSessionEnded() {
  for (const listener of sessionEndedListeners) listener();
}

// ---------------------------------------------------------------------------
// Attaching the credential
// ---------------------------------------------------------------------------

/** Endpoints that must never carry a bearer token or trigger a refresh. */
function isAuthEndpoint(url: string | undefined): boolean {
  if (!url) return false;
  return (
    url.endsWith(routes.api.auth.token.obtain()) ||
    url.endsWith(routes.api.auth.token.refresh()) ||
    url.endsWith(routes.api.auth.token.revoke()) ||
    url.endsWith(routes.api.auth.token.verifyTwoFactor())
  );
}

http.interceptors.request.use((config) => {
  const tokens = currentTokens();
  if (tokens && !isAuthEndpoint(config.url)) {
    config.headers.set('Authorization', `Bearer ${tokens.access}`);
  }
  return config;
});

// ---------------------------------------------------------------------------
// Refreshing
// ---------------------------------------------------------------------------

let inFlightRefresh: Promise<string | null> | null = null;

/**
 * Get a fresh access token, starting a refresh only if one is not already
 * running. Resolves to null when the session is over for good.
 */
function refreshAccessToken(): Promise<string | null> {
  inFlightRefresh ??= (async () => {
    const tokens = currentTokens();
    if (!tokens) return null;

    try {
      // A bare axios call, not `http`: going back through this instance would
      // re-enter the interceptor below on a 401 and recurse.
      const response = await axios.post<ApiEnvelope<TokenPair>>(
        routes.api.auth.token.refresh(),
        { refresh: tokens.refresh },
        { headers: { 'Content-Type': 'application/json' }, timeout: 20000 },
      );

      const pair = response.data.data;
      if (!pair?.access || !pair.refresh) return null;

      // Rotation is on, so this response carries a *new* refresh token and
      // the old one is already blacklisted. Failing to store both here is
      // what turns "signed in for a month" into "signed out in 15 minutes".
      await saveTokens({ access: pair.access, refresh: pair.refresh });
      return pair.access;
    } catch {
      return null;
    } finally {
      // Cleared inside the same promise so the next 401 after this settles
      // starts a fresh attempt rather than awaiting a resolved one.
      inFlightRefresh = null;
    }
  })();

  return inFlightRefresh;
}

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryableConfig | undefined;

    const isExpiredToken =
      error.response?.status === 401 &&
      config &&
      !config._retried &&
      !isAuthEndpoint(config.url) &&
      currentTokens() !== null;

    if (!isExpiredToken) {
      return Promise.reject(error);
    }

    const access = await refreshAccessToken();

    if (!access) {
      // The refresh token is spent, revoked or expired. Nothing this client
      // holds can recover the session, so drop it rather than leaving a
      // credential around that produces a 401 on every screen.
      await clearTokens();
      announceSessionEnded();
      return Promise.reject(error);
    }

    // Retried exactly once. A second 401 on the same request means the token
    // is not the problem, and retrying again would loop.
    config._retried = true;
    config.headers.set('Authorization', `Bearer ${access}`);
    return http.request(config);
  },
);

export const { apiCall, apiData } = createApiClient(http);

/** Test seam: forget any refresh currently in flight. */
export function resetRefreshState(): void {
  inFlightRefresh = null;
}

export { toApiError };
