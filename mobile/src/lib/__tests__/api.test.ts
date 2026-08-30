/**
 * The client's recovery from an expired access token.
 *
 * This is the part of the app most likely to be wrong in a way nobody notices
 * until it is in someone's hands: everything works for fifteen minutes, and
 * then the failure depends on how many screens happened to be fetching at
 * once. So the tests drive it through axios itself, with a fake adapter,
 * rather than calling the interceptor directly -- the ordering is the thing
 * being tested.
 */

import axios, { AxiosError, type AxiosAdapter, type AxiosResponse } from 'axios';

import { apiCall, http, onSessionEnded, resetRefreshState } from '../api';
import { routes } from '../routes';
import { currentTokens, resetTokenCache, saveTokens } from '../tokenStore';

const realAdapter = http.defaults.adapter;

/**
 * Build a response the way axios's own adapters do.
 *
 * A custom adapter is responsible for rejecting on a failing status -- axios
 * takes whatever it resolves with at face value. An adapter that resolved a
 * 401 would test nothing, because the interceptor under test only ever sees
 * rejections.
 */
function answer(config: Parameters<AxiosAdapter>[0], status: number, data: unknown) {
  const response = { status, statusText: '', headers: {}, config, data } as AxiosResponse;
  if (status >= 400) {
    throw new AxiosError('Request failed', String(status), config, null, response);
  }
  return response;
}

/** An adapter that answers each request from a queue of status codes. */
function respondWith(statuses: number[]): AxiosAdapter {
  const queue = [...statuses];
  return async (config) => {
    const status = queue.shift() ?? 200;
    return answer(config, status, {
      status: status < 400 ? 'success' : 'error',
      data: { ok: true },
    });
  };
}

beforeEach(async () => {
  resetTokenCache();
  resetRefreshState();
  await saveTokens({ access: 'expired-access', refresh: 'good-refresh' });
  jest.restoreAllMocks();
});

afterAll(() => {
  http.defaults.adapter = realAdapter;
});

/** Stub the bare-axios POST the refresh uses. */
function mockRefresh(pair: { access: string; refresh: string } | null) {
  return jest.spyOn(axios, 'post').mockImplementation(async () => {
    if (pair === null) throw new Error('refresh refused');
    return { data: { status: 'success', data: { ...pair, access_expires_in: 900 } } };
  });
}

describe('attaching the credential', () => {
  it('sends the access token as a bearer', async () => {
    const seen: string[] = [];
    http.defaults.adapter = async (config) => {
      seen.push(String(config.headers?.Authorization));
      return answer(config, 200, { status: 'success' });
    };

    await apiCall({ url: routes.api.users.me() });

    expect(seen).toEqual(['Bearer expired-access']);
  });

  it('does not send one to the token endpoints', async () => {
    const seen: (string | undefined)[] = [];
    http.defaults.adapter = async (config) => {
      seen.push(config.headers?.Authorization as string | undefined);
      return answer(config, 200, { status: 'success' });
    };

    await apiCall({ url: routes.api.auth.token.obtain(), method: 'POST' });

    expect(seen).toEqual([undefined]);
  });
});

describe('recovering from a 401', () => {
  it('refreshes and retries the original request', async () => {
    mockRefresh({ access: 'fresh-access', refresh: 'fresh-refresh' });
    http.defaults.adapter = respondWith([401, 200]);

    const envelope = await apiCall<{ ok: boolean }>({ url: routes.api.users.me() });

    expect(envelope.data).toEqual({ ok: true });
    expect(currentTokens()).toEqual({ access: 'fresh-access', refresh: 'fresh-refresh' });
  });

  it('stores the rotated refresh token, not just the access token', async () => {
    // Rotation means the refresh token in the response is a *new* one and the
    // old is already blacklisted. Keeping only the access token turns "signed
    // in for a month" into "signed out in fifteen minutes".
    mockRefresh({ access: 'fresh-access', refresh: 'rotated-refresh' });
    http.defaults.adapter = respondWith([401, 200]);

    await apiCall({ url: routes.api.users.me() });

    expect(currentTokens()?.refresh).toBe('rotated-refresh');
  });

  it('refreshes once for a burst of simultaneous 401s', async () => {
    // The failure this prevents: an app coming out of the background fires
    // several requests at once, all 401. Refreshing per 401 spends the
    // rotating refresh token more than once, so all but the first fail -- and
    // the user is thrown back to the sign-in screen for no visible reason.
    const post = mockRefresh({ access: 'fresh-access', refresh: 'fresh-refresh' });
    http.defaults.adapter = respondWith([401, 401, 401, 200, 200, 200]);

    await Promise.all([
      apiCall({ url: routes.api.users.me() }),
      apiCall({ url: routes.api.files.list() }),
      apiCall({ url: routes.api.apiKeys.list() }),
    ]);

    expect(post).toHaveBeenCalledTimes(1);
  });

  it('gives up after one retry rather than looping', async () => {
    mockRefresh({ access: 'fresh-access', refresh: 'fresh-refresh' });
    http.defaults.adapter = respondWith([401, 401]);

    await expect(apiCall({ url: routes.api.users.me() })).rejects.toThrow();
  });

  it('does not try to refresh when there is no session to refresh', async () => {
    resetTokenCache();
    const post = mockRefresh({ access: 'a', refresh: 'r' });
    http.defaults.adapter = respondWith([401]);

    await expect(apiCall({ url: routes.api.users.me() })).rejects.toThrow();
    expect(post).not.toHaveBeenCalled();
  });
});

describe('when the session is really over', () => {
  it('drops the tokens and announces it', async () => {
    // The client cannot navigate, so it publishes the fact and the auth store
    // reacts. Without this the app keeps rendering signed-in screens that
    // 401 one at a time.
    mockRefresh(null);
    http.defaults.adapter = respondWith([401]);

    const listener = jest.fn();
    const unsubscribe = onSessionEnded(listener);

    await expect(apiCall({ url: routes.api.users.me() })).rejects.toThrow();

    expect(currentTokens()).toBeNull();
    expect(listener).toHaveBeenCalledTimes(1);
    unsubscribe();
  });

  it('stops calling a listener that unsubscribed', async () => {
    mockRefresh(null);
    http.defaults.adapter = respondWith([401]);

    const listener = jest.fn();
    onSessionEnded(listener)();

    await expect(apiCall({ url: routes.api.users.me() })).rejects.toThrow();

    expect(listener).not.toHaveBeenCalled();
  });
});

describe('the envelope', () => {
  it('turns a failure into a field-addressable error', async () => {
    http.defaults.adapter = async (config) =>
      answer(config, 400, {
        status: 'error',
        message: 'Registration failed.',
        errors: { email: ['A user with that email already exists.'] },
      });

    const error = await apiCall({ url: routes.api.auth.register(), method: 'POST' }).catch(
      (thrown) => thrown,
    );

    expect(error.message).toBe('Registration failed.');
    expect(error.fieldError('email')).toBe('A user with that email already exists.');
  });
});
