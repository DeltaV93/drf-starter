/**
 * The single HTTP client.
 *
 * Session-cookie auth means two things have to be right on every unsafe
 * request: the cookies must be sent (withCredentials) and the CSRF token must
 * be echoed back in the X-CSRFToken header. Both are handled here so no call
 * site has to remember.
 *
 * The token is read from the csrftoken cookie, which Django sets and
 * deliberately leaves readable by JavaScript. If it is missing -- first visit,
 * or the cookie expired -- the interceptor fetches one before retrying.
 */

import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';

import { routes } from './routes';
import type { ApiEnvelope } from './types';

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

export class ApiError extends Error {
  readonly status: number | undefined;
  readonly fieldErrors: Record<string, string[] | string>;

  constructor(message: string, status?: number, fieldErrors = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.fieldErrors = fieldErrors;
  }

  /** The first message for a field, for wiring straight into a form. */
  fieldError(field: string): string | undefined {
    const value = this.fieldErrors[field];
    if (!value) return undefined;
    return Array.isArray(value) ? value[0] : value;
  }
}

function toApiError(error: unknown, fallback: string): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiEnvelope>;
    const envelope = axiosError.response?.data;
    return new ApiError(
      envelope?.message || axiosError.message || fallback,
      axiosError.response?.status,
      envelope?.errors ?? {},
    );
  }
  return new ApiError(fallback);
}

/**
 * Make a request and unwrap the response envelope.
 *
 * Throws ApiError on failure so callers can `try/catch` rather than inspect
 * status codes.
 */
export async function apiCall<T = unknown>(
  config: AxiosRequestConfig & { errorMessage?: string },
): Promise<ApiEnvelope<T>> {
  const { errorMessage = 'Something went wrong. Please try again.', ...axiosConfig } = config;

  try {
    const response = await http.request<ApiEnvelope<T>>(axiosConfig);
    return response.data;
  } catch (error) {
    throw toApiError(error, errorMessage);
  }
}

/** Same as apiCall but returns just the `data` payload. */
export async function apiData<T>(
  config: AxiosRequestConfig & { errorMessage?: string },
): Promise<T | undefined> {
  const envelope = await apiCall<T>(config);
  return envelope.data;
}
