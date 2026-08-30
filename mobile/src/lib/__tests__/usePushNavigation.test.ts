/**
 * Tapping a notification opens the screen it names.
 *
 * Registration without this is half a feature: the notification shows, the
 * person taps it, and the app opens wherever it happened to be.
 */

import { renderHook } from '@testing-library/react-native';
import * as Notifications from 'expo-notifications';

import { usePushNavigation } from '../usePushNavigation';

const mockPush = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush }),
}));

function tapped(path: unknown, identifier = 'n1') {
  return {
    notification: {
      request: { identifier, content: { data: path === undefined ? {} : { path } } },
    },
  };
}

beforeEach(() => {
  jest.clearAllMocks();
});

it('navigates to the path the notification carries', async () => {
  jest.mocked(Notifications.useLastNotificationResponse).mockReturnValue(
    tapped('/organization') as never,
  );

  await renderHook(() => usePushNavigation());

  expect(mockPush).toHaveBeenCalledWith('/organization');
});

it('does nothing when no notification was tapped', async () => {
  jest.mocked(Notifications.useLastNotificationResponse).mockReturnValue(null);

  await renderHook(() => usePushNavigation());

  expect(mockPush).not.toHaveBeenCalled();
});

it('does nothing when the payload names no path', async () => {
  jest.mocked(Notifications.useLastNotificationResponse).mockReturnValue(
    tapped(undefined) as never,
  );

  await renderHook(() => usePushNavigation());

  expect(mockPush).not.toHaveBeenCalled();
});

it('will not follow a payload out of the app', async () => {
  // A push payload is not this app's code. It is whatever reached the push
  // service with your credentials.
  jest.mocked(Notifications.useLastNotificationResponse).mockReturnValue(
    tapped('https://evil.example.com') as never,
  );

  await renderHook(() => usePushNavigation());

  expect(mockPush).toHaveBeenCalledWith('/profile');
});

it('navigates once, not on every render', async () => {
  // The hook returns the same response for the life of the process, so an
  // effect without a guard fights the user's own navigation continuously.
  jest.mocked(Notifications.useLastNotificationResponse).mockReturnValue(
    tapped('/files') as never,
  );

  const view = await renderHook(() => usePushNavigation());
  // Awaited: RTL 14 renders concurrently, and overlapping un-awaited
  // rerenders trip React's own act() warning.
  await view.rerender({});
  await view.rerender({});

  expect(mockPush).toHaveBeenCalledTimes(1);
});
