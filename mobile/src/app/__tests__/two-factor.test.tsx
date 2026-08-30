/**
 * The second step of a sign-in, and the state it has to refuse.
 *
 * The challenge is redeemable for a session and lives in one place: this
 * screen's route parameters. Arriving without one -- a deep link, a reload in
 * development, a stale back-stack -- has to say so rather than showing a form
 * that can only fail.
 */

import TwoFactorScreen from '../two-factor';
import { renderWithProviders, userEvent, waitFor } from '../../test/utils';

const mockReplace = jest.fn();
const mockParams: { challenge?: string; redirect?: string } = {};

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: jest.fn(), replace: mockReplace }),
  useLocalSearchParams: () => mockParams,
}));

const mockVerify = jest.fn();

jest.mock('../../store/auth', () => ({
  useAuth: () => ({ verifyTwoFactor: mockVerify }),
}));

const mockToastError = jest.fn();

jest.mock('../../store/toast', () => ({
  useToast: () => ({ error: mockToastError, success: jest.fn(), info: jest.fn() }),
}));

beforeEach(() => {
  jest.clearAllMocks();
  delete mockParams.challenge;
  delete mockParams.redirect;
});

describe('without a challenge', () => {
  it('says to start again rather than showing a form that cannot work', async () => {
    const view = await renderWithProviders(<TwoFactorScreen />);

    expect(view.getByText('Start again')).toBeTruthy();
    expect(view.queryByLabelText('Code')).toBeNull();
  });

  it('offers a way back to sign in', async () => {
    const user = userEvent.setup();
    const view = await renderWithProviders(<TwoFactorScreen />);

    await user.press(view.getByText('Back to log in'));

    expect(mockReplace).toHaveBeenCalledWith('/login');
  });
});

describe('with a challenge', () => {
  beforeEach(() => {
    mockParams.challenge = 'signed-challenge';
  });

  it('exchanges the code for a session', async () => {
    mockVerify.mockResolvedValue({ id: 1 });
    const user = userEvent.setup();
    const view = await renderWithProviders(<TwoFactorScreen />);

    await user.type(view.getByLabelText('Code'), '123456');
    await user.press(view.getByText('Verify'));

    await waitFor(() => {
      expect(mockVerify).toHaveBeenCalledWith('signed-challenge', '123456');
      expect(mockReplace).toHaveBeenCalledWith('/profile');
    });
  });

  it('honours the destination the sign-in screen passed through', async () => {
    // The second factor is a detour inside a flow, not the end of one: an
    // invitation that stopped here still has to resume.
    mockParams.redirect = '/invitations/abc';
    mockVerify.mockResolvedValue({ id: 1 });
    const user = userEvent.setup();
    const view = await renderWithProviders(<TwoFactorScreen />);

    await user.type(view.getByLabelText('Code'), '123456');
    await user.press(view.getByText('Verify'));

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/invitations/abc'));
  });

  it('stays put when the code is refused', async () => {
    mockVerify.mockRejectedValue(new Error('nope'));
    const user = userEvent.setup();
    const view = await renderWithProviders(<TwoFactorScreen />);

    await user.type(view.getByLabelText('Code'), '000000');
    await user.press(view.getByText('Verify'));

    await waitFor(() => expect(mockToastError).toHaveBeenCalled());
    expect(mockReplace).not.toHaveBeenCalled();
  });
});
