/**
 * The half of the HTTP client that has nothing to do with the platform.
 *
 * What differs between the website and the mobile app is only how a request
 * proves who is making it: the browser sends a session cookie and echoes a
 * CSRF token, the phone sends a bearer token it refreshes itself. Neither of
 * those belongs here.
 *
 * What is identical is everything after the response arrives -- unwrapping the
 * `{status, message, data, errors}` envelope and turning a failure into an
 * error a form can read field by field. That is what lives here, so a change
 * to the envelope is one edit rather than two.
 */

import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
} from 'axios';

import type { ApiEnvelope } from './types';

export const DEFAULT_ERROR_MESSAGE = 'Something went wrong. Please try again.';

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

  /**
   * True when the request failed before it reached the backend.
   *
   * Worth distinguishing on mobile, where losing signal mid-request is
   * ordinary rather than exceptional and deserves a different message from
   * "the server said no".
   */
  get isNetworkError(): boolean {
    return this.status === undefined;
  }
}

/** Turn anything thrown by axios into an ApiError carrying the envelope. */
export function toApiError(error: unknown, fallback = DEFAULT_ERROR_MESSAGE): ApiError {
  if (error instanceof ApiError) return error;

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

export type ApiRequestConfig = AxiosRequestConfig & { errorMessage?: string };

/**
 * Bind `apiCall` / `apiData` to a configured axios instance.
 *
 * Each app supplies its own instance -- already carrying whichever auth
 * interceptor it needs -- and gets back the same two functions its call sites
 * use, so no screen knows which authentication scheme it is running under.
 */
export function createApiClient(http: AxiosInstance) {
  /**
   * Make a request and unwrap the response envelope.
   *
   * Throws ApiError on failure so callers can `try/catch` rather than inspect
   * status codes.
   */
  async function apiCall<T = unknown>(config: ApiRequestConfig): Promise<ApiEnvelope<T>> {
    const { errorMessage = DEFAULT_ERROR_MESSAGE, ...axiosConfig } = config;

    try {
      const response = await http.request<ApiEnvelope<T>>(axiosConfig);
      return response.data;
    } catch (error) {
      throw toApiError(error, errorMessage);
    }
  }

  /** Same as apiCall but returns just the `data` payload. */
  async function apiData<T>(config: ApiRequestConfig): Promise<T | undefined> {
    const envelope = await apiCall<T>(config);
    return envelope.data;
  }

  return { apiCall, apiData };
}
