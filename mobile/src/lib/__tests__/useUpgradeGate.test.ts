/**
 * How long the splash screen is allowed to wait for the version check.
 */

import type { UpgradeCheck } from '@app/shared/types';

import { act, renderHook, waitFor } from '../../test/utils';
import { checkForUpgrade } from '../upgrade';
import { useUpgradeGate } from '../useUpgradeGate';

jest.mock('../upgrade', () => ({ checkForUpgrade: jest.fn() }));

const mockCheck = checkForUpgrade as jest.MockedFunction<typeof checkForUpgrade>;

const none: UpgradeCheck = {
  requirement: 'none',
  minimum_version: '',
  recommended_version: '',
  store_url: '',
  message: '',
};

afterEach(() => {
  jest.useRealTimers();
  jest.clearAllMocks();
});

it('stops holding the splash as soon as the answer arrives', async () => {
  mockCheck.mockResolvedValue(none);

  const { result } = await renderHook(() => useUpgradeGate());

  await waitFor(() => expect(result.current.pending).toBe(false));
  expect(result.current.check).toEqual(none);
});

it('gives up on the splash after a deadline rather than waiting out the network', async () => {
  /**
   * The property that keeps a bad connection from costing every launch a
   * spinner. A blocked build is rare; a slow network is not, so the app comes
   * up and the wall drops later if it turns out to be needed.
   */
  jest.useFakeTimers();
  // Never resolves: a connection that is open and going nowhere.
  mockCheck.mockReturnValue(new Promise(() => {}));

  const { result } = await renderHook(() => useUpgradeGate());

  expect(result.current.pending).toBe(true);

  await act(async () => {
    jest.advanceTimersByTime(1500);
  });

  expect(result.current.pending).toBe(false);
  // Still unanswered -- nothing is blocked, which is the fail-open default.
  expect(result.current.check).toBeNull();
});

it('still reports a block that arrives after the deadline', async () => {
  // The app is already on screen by then. The wall drops on top of it, which
  // is the trade the deadline buys.
  jest.useFakeTimers();
  let answer: (value: UpgradeCheck) => void = () => {};
  mockCheck.mockReturnValue(new Promise((resolve) => (answer = resolve)));

  const { result } = await renderHook(() => useUpgradeGate());
  await act(async () => {
    jest.advanceTimersByTime(1500);
  });
  expect(result.current.pending).toBe(false);

  await act(async () => {
    answer({ ...none, requirement: 'required' });
  });

  expect(result.current.check?.requirement).toBe('required');
});
