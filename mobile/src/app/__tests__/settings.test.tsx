/**
 * Signing out, and the order it has to happen in.
 *
 * The ordering is the whole test. Unregistering the device is an
 * authenticated request, so it has to go before the tokens are cleared --
 * afterwards it is a request with no credential, it fails silently, and the
 * phone keeps receiving that account's notifications. On a shared device that
 * is somebody else reading your notifications.
 */

import SettingsScreen from '../(app)/settings';
import { renderWithProviders, userEvent, waitFor } from '../../test/utils';

const mockReplace = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: jest.fn(), replace: mockReplace }),
}));

/** Everything that happens on sign-out, in the order it happened. */
const order: string[] = [];

const mockLogout = jest.fn(async () => {
  order.push('logout');
});
const mockUnregister = jest.fn(async () => {
  order.push('unregister');
});
const mockForget = jest.fn(async () => {
  order.push('forget-organization');
});

jest.mock('../../store/auth', () => ({
  useAuth: () => ({ logout: mockLogout }),
}));

jest.mock('../../lib/push', () => ({
  unregisterFromPush: () => mockUnregister(),
}));

jest.mock('../../store/organization', () => ({
  useOrganizations: () => ({ forget: mockForget }),
}));

jest.mock('../../store/toast', () => ({
  useToast: () => ({ error: jest.fn(), success: jest.fn(), info: jest.fn() }),
}));

beforeEach(() => {
  jest.clearAllMocks();
  order.length = 0;
});

it('offers the appearance choices, including following the system', async () => {
  // Three states, not a boolean. A "dark mode" switch cannot express "follow
  // the phone", so an app built on one stops tracking the system schedule the
  // first time anyone touches it.
  const view = await renderWithProviders(<SettingsScreen />);

  expect(view.getByText('System')).toBeTruthy();
  expect(view.getByText('Light')).toBeTruthy();
  expect(view.getByText('Dark')).toBeTruthy();
});

it('unregisters the device before dropping the credential that authorises it', async () => {
  const user = userEvent.setup();
  const view = await renderWithProviders(<SettingsScreen />);

  await user.press(view.getByText('Log out'));

  await waitFor(() => expect(mockLogout).toHaveBeenCalled());
  expect(order.indexOf('unregister')).toBeLessThan(order.indexOf('logout'));
});

it('forgets the active organization too', async () => {
  // Otherwise the next person to sign in on this device inherits the last
  // one's `X-Organization` header.
  const user = userEvent.setup();
  const view = await renderWithProviders(<SettingsScreen />);

  await user.press(view.getByText('Log out'));

  await waitFor(() => expect(mockForget).toHaveBeenCalled());
});

it('returns to the sign-in screen', async () => {
  const user = userEvent.setup();
  const view = await renderWithProviders(<SettingsScreen />);

  await user.press(view.getByText('Log out'));

  await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/login'));
});
