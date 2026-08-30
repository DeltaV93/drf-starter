/**
 * Deleting an account from inside the app.
 *
 * Apple's 5.1.1(v) requires this to exist and to work here rather than on a
 * website, so the first assertion is simply that the screen is reachable and
 * does what it says. The rest are about not doing it by accident, and about
 * leaving nothing behind on the device afterwards.
 */

import DeleteAccountScreen from '../(app)/delete-account';
import { renderWithProviders, userEvent, waitFor } from '../../test/utils';

const mockReplace = jest.fn();
const mockBack = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: jest.fn(), replace: mockReplace, back: mockBack }),
}));

const order: string[] = [];
const mockApiCall = jest.fn(async () => {
  order.push('delete');
  return { status: 'success' };
});
const mockLogout = jest.fn(async () => {
  order.push('logout');
});
const mockUnregister = jest.fn(async () => {
  order.push('unregister');
});
const mockForget = jest.fn(async () => {
  order.push('forget');
});

jest.mock('../../lib/api', () => ({
  ...jest.requireActual('@app/shared/api'),
  apiCall: (...args: unknown[]) => mockApiCall(...(args as [])),
}));

jest.mock('../../store/auth', () => ({ useAuth: () => ({ logout: mockLogout }) }));
jest.mock('../../lib/push', () => ({ unregisterFromPush: () => mockUnregister() }));
jest.mock('../../store/organization', () => ({
  useOrganizations: () => ({ forget: mockForget }),
}));

const mockToastError = jest.fn();
jest.mock('../../store/toast', () => ({
  useToast: () => ({ error: mockToastError, success: jest.fn(), info: jest.fn() }),
}));

beforeEach(() => {
  jest.clearAllMocks();
  order.length = 0;
});

async function fillAndConfirm(view: Awaited<ReturnType<typeof renderWithProviders>>) {
  const user = userEvent.setup();
  await user.type(view.getByLabelText('Your password'), 'correct horse');
  // The screen title and the button share their wording, so take the button.
  await user.press(view.getAllByText('Delete account').at(-1)!);
  await user.press(view.getByText('Delete permanently'));
  return user;
}

it('will not submit without the password the backend requires', async () => {
  const user = userEvent.setup();
  const view = await renderWithProviders(<DeleteAccountScreen />);

  await user.press(view.getAllByText('Delete account').at(-1)!);

  // The confirmation never opens, so nothing can be sent.
  expect(view.queryByText('Delete permanently')).toBeNull();
  expect(mockApiCall).not.toHaveBeenCalled();
});

it('asks a second time before doing anything irreversible', async () => {
  const user = userEvent.setup();
  const view = await renderWithProviders(<DeleteAccountScreen />);

  await user.type(view.getByLabelText('Your password'), 'correct horse');
  await user.press(view.getAllByText('Delete account').at(-1)!);

  expect(view.getByText('Delete this account?')).toBeTruthy();
  expect(mockApiCall).not.toHaveBeenCalled();
});

it('sends the password and the optional reason', async () => {
  const view = await renderWithProviders(<DeleteAccountScreen />);
  await fillAndConfirm(view);

  await waitFor(() =>
    expect(mockApiCall).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'POST',
        data: { password: 'correct horse', reason: '' },
      }),
    ),
  );
});

it('leaves nothing signed in on the device afterwards', async () => {
  // The account is deactivated server-side, so every stored credential is
  // already dead. Clearing locally is what stops the next launch showing a
  // signed-in shell that 401s on every screen.
  const view = await renderWithProviders(<DeleteAccountScreen />);
  await fillAndConfirm(view);

  await waitFor(() => expect(mockLogout).toHaveBeenCalled());
  expect(mockForget).toHaveBeenCalled();
  expect(mockReplace).toHaveBeenCalledWith('/');
});

it('unregisters the device while the credential still authorises it', async () => {
  const view = await renderWithProviders(<DeleteAccountScreen />);
  await fillAndConfirm(view);

  await waitFor(() => expect(mockLogout).toHaveBeenCalled());
  expect(order.indexOf('unregister')).toBeLessThan(order.indexOf('logout'));
});

it('stays put when the password is wrong', async () => {
  mockApiCall.mockRejectedValueOnce(new Error('nope'));
  const view = await renderWithProviders(<DeleteAccountScreen />);
  await fillAndConfirm(view);

  await waitFor(() => expect(mockToastError).toHaveBeenCalled());
  expect(mockLogout).not.toHaveBeenCalled();
  expect(mockReplace).not.toHaveBeenCalled();
});
