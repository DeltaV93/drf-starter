/**
 * The single HTTP client for the browser.
 *
 * Session-cookie auth means two things have to be right on every unsafe
 * request: the cookies must be sent (withCredentials) and the CSRF token must
 * be echoed back in the X-CSRFToken header. Both are handled here so no call
 * site has to remember.
 *
 * The token is read from the csrftoken cookie, which Django sets and
 * deliberately leaves readable by JavaScript. If it is missing -- first visit,
 * or the cookie expired -- the interceptor fetches one before retrying.
 *
 * Everything downstream of the response -- unwrapping the envelope, turning a
 * failure into a field-addressable ApiError -- is in `@app/shared/api`, which
 * the mobile client uses too. Only the part above this line is web-specific.
 */

import axios, { type AxiosInstance } from 'axios';

import { createApiClient } from '@app/shared/api';
import type { ApiEnvelope } from '@app/shared/types';

import { routes } from './routes';

export { ApiError } from '@app/shared/api';

const CSRF_COOKIE = 'csrftoken';
const CSRF_HEADER = 'X-CSRFToken';
const UNSAFE_METHODS = new Set(['post', 'put', 'patch', 'delete']);

export function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export const http: AxiosInstance = axios.create({
  headers: { 'Content-Type': 'application/json' },
  // Required for the session and csrftoken cookies to travel at all.
  withCredentials: true,
});

/** Ask the backend to set a CSRF cookie. Safe to call more than once. */
export async function ensureCsrfToken(): Promise<string | null> {
  const existing = readCookie(CSRF_COOKIE);
  if (existing) return existing;

  try {
    const response = await http.get<ApiEnvelope<{ csrfToken: string }>>(routes.api.auth.csrf());
    return response.data.data?.csrfToken ?? readCookie(CSRF_COOKIE);
  } catch {
    return null;
  }
}

http.interceptors.request.use(async (config) => {
  const method = (config.method ?? 'get').toLowerCase();
  if (!UNSAFE_METHODS.has(method)) return config;

  const token = await ensureCsrfToken();
  if (token) {
    config.headers.set(CSRF_HEADER, token);
  }
  return config;
});

export const { apiCall, apiData } = createApiClient(http);
