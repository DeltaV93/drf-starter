/**
 * The update path, and chiefly the thing it must not do.
 */

import * as Updates from 'expo-updates';

import { fetchUpdateInBackground, resetUpdateThrottle } from '../updates';

const mockUpdates = Updates as jest.Mocked<typeof Updates> & { isEnabled: boolean };

beforeEach(() => {
  jest.clearAllMocks();
  resetUpdateThrottle();
  mockUpdates.isEnabled = true;
  mockUpdates.checkForUpdateAsync.mockResolvedValue({ isAvailable: false } as never);
  mockUpdates.fetchUpdateAsync.mockResolvedValue({ isNew: true } as never);
});

it('downloads an available update', async () => {
  mockUpdates.checkForUpdateAsync.mockResolvedValue({ isAvailable: true } as never);

  await expect(fetchUpdateInBackground()).resolves.toBe(true);
  expect(mockUpdates.fetchUpdateAsync).toHaveBeenCalled();
});

it('never reloads the app itself', async () => {
  /**
   * The whole policy in one assertion. Downloading is invisible; reloading
   * restarts the app under whoever is using it and loses what they typed.
   * expo-updates applies the fetched bundle on the next cold start on its
   * own, so this call is never the one that is missing.
   */
  mockUpdates.checkForUpdateAsync.mockResolvedValue({ isAvailable: true } as never);

  await fetchUpdateInBackground();

  expect(mockUpdates.reloadAsync).not.toHaveBeenCalled();
});

it('does nothing when updates are not configured', async () => {
  // Every checkout of this template until someone runs `eas init`.
  mockUpdates.isEnabled = false;

  await expect(fetchUpdateInBackground()).resolves.toBe(false);
  expect(mockUpdates.checkForUpdateAsync).not.toHaveBeenCalled();
});

it('survives the update server being unreachable', async () => {
  // An app that will not start because it could not reach an update server
  // is a worse outcome than an app running last week's bundle.
  mockUpdates.checkForUpdateAsync.mockRejectedValue(new Error('offline'));

  await expect(fetchUpdateInBackground()).resolves.toBe(false);
});

it('does not ask again on every foreground', async () => {
  /**
   * An app is foregrounded dozens of times a day. Checking on each one is a
   * request per switch, on a mobile connection, for a bundle that changes
   * weekly at best.
   */
  await fetchUpdateInBackground();
  await fetchUpdateInBackground();

  expect(mockUpdates.checkForUpdateAsync).toHaveBeenCalledTimes(1);
});
