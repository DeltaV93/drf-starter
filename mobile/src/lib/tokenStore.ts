/**
 * Where the token pair lives between launches.
 *
 * The keychain on iOS and the Keystore-backed shared preferences on Android,
 * via expo-secure-store. Not AsyncStorage: that is a plaintext file inside the
 * app's sandbox, readable by anything with filesystem access to a rooted or
 * jailbroken device, and a refresh token is a month-long credential.
 *
 * Every function here is defensive about the store being unavailable. It can
 * be: SecureStore throws on a device with no passcode set under some keychain
 * accessibility settings, and it is unimplemented on web. A failure to *read*
 * has to look like "not signed in" rather than crash the launch, because the
 * alternative is an app that cannot start.
 */

import * as SecureStore from 'expo-secure-store';

const ACCESS_KEY = 'auth.access';
const REFRESH_KEY = 'auth.refresh';

export interface StoredTokens {
  access: string;
  refresh: string;
}

/**
 * Keep the tokens in memory as well as in the store.
 *
 * SecureStore is asynchronous and, on a cold keychain, not especially fast --
 * paying that on every request would put a keychain read in front of every
 * screen. The cache is authoritative once the process is warm; the store is
 * what survives a relaunch.
 */
let cached: StoredTokens | null = null;
let loaded = false;

export async function loadTokens(): Promise<StoredTokens | null> {
  if (loaded) return cached;

  try {
    const [access, refresh] = await Promise.all([
      SecureStore.getItemAsync(ACCESS_KEY),
      SecureStore.getItemAsync(REFRESH_KEY),
    ]);
    // Both or neither. A half-written pair is worse than none: an access
    // token with no refresh token expires into a session that cannot be
    // recovered and cannot be distinguished from a real one.
    cached = access && refresh ? { access, refresh } : null;
  } catch {
    cached = null;
  }

  loaded = true;
  return cached;
}

/** What the interceptor reads. Synchronous on purpose -- see `cached`. */
export function currentTokens(): StoredTokens | null {
  return cached;
}

export async function saveTokens(tokens: StoredTokens): Promise<void> {
  cached = tokens;
  loaded = true;
  try {
    await Promise.all([
      SecureStore.setItemAsync(ACCESS_KEY, tokens.access),
      SecureStore.setItemAsync(REFRESH_KEY, tokens.refresh),
    ]);
  } catch {
    // The session still works for this launch -- `cached` is set -- it just
    // will not survive a restart. Failing the sign-in over that would be a
    // worse trade than quietly signing in.
  }
}

export async function clearTokens(): Promise<void> {
  cached = null;
  loaded = true;
  try {
    await Promise.all([
      SecureStore.deleteItemAsync(ACCESS_KEY),
      SecureStore.deleteItemAsync(REFRESH_KEY),
    ]);
  } catch {
    // Nothing useful to do. The in-memory copy is gone either way, which is
    // what stops this process from using them again.
  }
}

/** Test seam: forget that the store has been read. */
export function resetTokenCache(): void {
  cached = null;
  loaded = false;
}
