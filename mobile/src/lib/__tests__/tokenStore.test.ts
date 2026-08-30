import * as SecureStore from 'expo-secure-store';

import {
  clearTokens,
  currentTokens,
  loadTokens,
  resetTokenCache,
  saveTokens,
} from '../tokenStore';

const store = (SecureStore as unknown as { __store: Map<string, string> }).__store;

beforeEach(() => {
  store.clear();
  resetTokenCache();
  jest.clearAllMocks();
});

describe('loading', () => {
  it('returns null when nothing has been stored', async () => {
    await expect(loadTokens()).resolves.toBeNull();
  });

  it('returns the pair that was stored', async () => {
    await saveTokens({ access: 'a', refresh: 'r' });
    resetTokenCache();

    await expect(loadTokens()).resolves.toEqual({ access: 'a', refresh: 'r' });
  });

  it('refuses a half-written pair', async () => {
    // An access token with no refresh token expires into a session that
    // cannot be recovered and cannot be told apart from a real one, so it has
    // to read as "not signed in" rather than as "signed in for 15 minutes".
    store.set('auth.access', 'orphan');

    await expect(loadTokens()).resolves.toBeNull();
  });

  it('reads the keystore once, not once per request', async () => {
    await loadTokens();
    await loadTokens();

    // Two keys, one read each. A keychain read in front of every API call
    // would put a native round trip on the path of every screen.
    expect(SecureStore.getItemAsync).toHaveBeenCalledTimes(2);
  });

  it('treats an unreadable keystore as signed out rather than crashing', async () => {
    // SecureStore throws on some devices with no passcode set. An app that
    // cannot start is a worse answer than an app that asks you to sign in.
    jest.mocked(SecureStore.getItemAsync).mockRejectedValueOnce(new Error('locked'));

    await expect(loadTokens()).resolves.toBeNull();
  });
});

describe('saving and clearing', () => {
  it('makes the pair readable synchronously, for the interceptor', async () => {
    await saveTokens({ access: 'a', refresh: 'r' });

    expect(currentTokens()).toEqual({ access: 'a', refresh: 'r' });
  });

  it('signs in for this launch even when the keystore write fails', async () => {
    jest.mocked(SecureStore.setItemAsync).mockRejectedValue(new Error('full'));

    await saveTokens({ access: 'a', refresh: 'r' });

    // The session works; it just will not survive a restart. Failing the
    // sign-in over that would be the worse trade.
    expect(currentTokens()).toEqual({ access: 'a', refresh: 'r' });
  });

  it('forgets the pair in memory and in the keystore', async () => {
    await saveTokens({ access: 'a', refresh: 'r' });

    await clearTokens();

    expect(currentTokens()).toBeNull();
    expect(store.size).toBe(0);
  });
});
