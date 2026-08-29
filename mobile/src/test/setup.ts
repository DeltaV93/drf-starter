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

/* eslint-disable @typescript-eslint/no-require-imports */

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

jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);

jest.mock('expo-localization', () => ({
  getLocales: () => [{ languageCode: 'en', languageTag: 'en-GB' }],
}));

jest.mock('expo-device', () => ({ isDevice: true, deviceName: 'Test device' }));

jest.mock('expo-notifications', () => ({
  getPermissionsAsync: jest.fn(async () => ({ granted: true, canAskAgain: true })),
  requestPermissionsAsync: jest.fn(async () => ({ granted: true })),
  getExpoPushTokenAsync: jest.fn(async () => ({ data: 'ExponentPushToken[test]' })),
}));
