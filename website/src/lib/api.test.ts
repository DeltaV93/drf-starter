import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError, apiCall, ensureCsrfToken, http, readCookie } from './api';

function setCookie(name: string, value: string) {
  document.cookie = `${name}=${value}; path=/`;
}

describe('readCookie', () => {
  it('reads a cookie by name', () => {
    setCookie('csrftoken', 'abc123');

    expect(readCookie('csrftoken')).toBe('abc123');
  });

  it('returns null when the cookie is absent', () => {
    expect(readCookie('nope')).toBeNull();
  });

  it('does not match a cookie whose name merely ends with the query', () => {
    setCookie('xcsrftoken', 'wrong');

    expect(readCookie('csrftoken')).toBeNull();
  });
});

describe('ensureCsrfToken', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('uses the existing cookie without a request', async () => {
    setCookie('csrftoken', 'already-here');
    const get = vi.spyOn(http, 'get');

    await expect(ensureCsrfToken()).resolves.toBe('already-here');
    expect(get).not.toHaveBeenCalled();
  });

  it('fetches a token when the cookie is missing', async () => {
    vi.spyOn(http, 'get').mockResolvedValue({
      data: { status: 'success', data: { csrfToken: 'fetched' } },
    });

    await expect(ensureCsrfToken()).resolves.toBe('fetched');
  });

  it('resolves to null rather than throwing when the request fails', async () => {
    vi.spyOn(http, 'get').mockRejectedValue(new Error('offline'));

    await expect(ensureCsrfToken()).resolves.toBeNull();
  });
});

describe('apiCall', () => {
  it('returns the response envelope', async () => {
    vi.spyOn(http, 'request').mockResolvedValue({
      data: { status: 'success', data: { id: 1 } },
    });

    const envelope = await apiCall<{ id: number }>({ url: '/x', method: 'GET' });

    expect(envelope.data).toEqual({ id: 1 });
  });

  it('throws an ApiError carrying the backend message and field errors', async () => {
    const axiosError = Object.assign(new Error('Request failed'), {
      isAxiosError: true,
      response: {
        status: 400,
        data: {
          status: 'error',
          message: 'Registration failed.',
          errors: { email: ['A user with that email already exists.'] },
        },
      },
    });
    vi.spyOn(http, 'request').mockRejectedValue(axiosError);

    const error = await apiCall({ url: '/x', method: 'POST' }).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe('Registration failed.');
    expect(error.status).toBe(400);
    expect(error.fieldError('email')).toBe('A user with that email already exists.');
  });

  it('falls back to the supplied errorMessage for a non-HTTP failure', async () => {
    vi.spyOn(http, 'request').mockRejectedValue(new Error('boom'));

    const error = await apiCall({ url: '/x', errorMessage: 'Could not load.' }).catch((e) => e);

    expect(error.message).toBe('Could not load.');
  });
});

describe('ApiError.fieldError', () => {
  it('handles both a list of messages and a bare string', () => {
    const error = new ApiError('Bad', 400, { a: ['first', 'second'], b: 'only' });

    expect(error.fieldError('a')).toBe('first');
    expect(error.fieldError('b')).toBe('only');
    expect(error.fieldError('missing')).toBeUndefined();
  });
});
