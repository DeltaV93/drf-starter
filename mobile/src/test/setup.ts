/// <reference types="jest" />

/**
 * What the tests stand in for.
 *
 * Everything mocked here is a native module: real code behind a JavaScript
 * interface, with nothing behind it in Node. The mocks are deliberately
 * behavioural rather than empty -- an in-memory keystore that actually stores
 * is what lets `tokenStore` be tested at all, and a no-op one would let a
 * broken implementation pass.
 */

/**
 * Every optional feature on, for the tests.
 *
 * `lib/config.ts` reads these once at import time, which is what Expo's
 * build-time substitution requires -- so they have to be set here, in a
 * setup file, before anything under test is imported.
 *
 * On rather than off because a flag-off screen renders a single explanatory
 * card, and a suite that exercised only that would pass while every real
 * screen was broken. `FeatureOff` has its own coverage for the other
 * direction.
 */
for (const flag of [
  'STRIPE_ENABLED',
  'ORGANIZATIONS_ENABLED',
  'TWO_FACTOR_ENABLED',
  'API_KEYS_ENABLED',
  'UPLOADS_ENABLED',
  'AUDIT_LOG_ENABLED',
  'SOCIAL_AUTH_ENABLED',
  'MCP_CLIENT_ENABLED',
  'PUSH_ENABLED',
]) {
  process.env[`EXPO_PUBLIC_${flag}`] = 'true';
}

jest.mock('expo-secure-store', () => {
  const store = new Map<string, string>();
  return {
    getItemAsync: jest.fn(async (key: string) => store.get(key) ?? null),
    setItemAsync: jest.fn(async (key: string, value: string) => {
      store.set(key, value);
    }),
    deleteItemAsync: jest.fn(async (key: string) => {
      store.delete(key);
    }),
    __store: store,
  };
});
// Hand-written rather than the package's own jest mock: version 3 no longer
// ships one, and the import failure only surfaced when a test first pulled in
// a module that reads storage. An in-memory store rather than no-ops, so a
// preference that is written can be read back.
jest.mock('@react-native-async-storage/async-storage', () => {
  const store = new Map<string, string>();
  return {
    __esModule: true,
    default: {
      getItem: jest.fn(async (key: string) => store.get(key) ?? null),
      setItem: jest.fn(async (key: string, value: string) => {
        store.set(key, value);
      }),
      removeItem: jest.fn(async (key: string) => {
        store.delete(key);
      }),
      clear: jest.fn(async () => store.clear()),
    },
  };
});
jest.mock('expo-localization', () => ({
  getLocales: () => [{ languageCode: 'en', languageTag: 'en-GB' }],
}));
jest.mock('expo-device', () => ({ isDevice: true, deviceName: 'Test device' }));
jest.mock('expo-notifications', () => ({
  getPermissionsAsync: jest.fn(async () => ({ granted: true, canAskAgain: true })),
  requestPermissionsAsync: jest.fn(async () => ({ granted: true })),
  getExpoPushTokenAsync: jest.fn(async () => ({ data: 'ExponentPushToken[test]' })),
  // Called at module load by `lib/push.ts`; a mock without it throws on
  // import rather than in a test, which is a confusing place to find out.
  setNotificationHandler: jest.fn(),
  // Defaults to "nothing was tapped", which is every launch. Tests that care
  // override it.
  useLastNotificationResponse: jest.fn(() => null),
}));

/**
 * Over-the-air updates.
 *
 * `isEnabled` false by default, which is what a real build without an EAS
 * project reports -- so a test that does not opt in exercises the same path a
 * plain checkout runs. The tests that care flip it.
 */
jest.mock('expo-updates', () => ({
  isEnabled: false,
  checkForUpdateAsync: jest.fn(async () => ({ isAvailable: false })),
  fetchUpdateAsync: jest.fn(async () => ({ isNew: true })),
  // Present so a test that calls it fails loudly rather than silently
  // reloading nothing. Applying an update on the spot is the thing
  // `lib/updates.ts` must never do.
  reloadAsync: jest.fn(async () => {
    throw new Error('reloadAsync must not be called: updates apply on next cold start');
  }),
}));

jest.mock('expo-application', () => ({
  nativeApplicationVersion: '1.0.0',
  nativeBuildVersion: '1',
}));
