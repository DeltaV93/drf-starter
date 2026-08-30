/**
 * Accepting an invitation, including the detour through sign-in.
 *
 * This screen's URL carries the only copy of the invitation token, so every
 * assertion here is really about one thing: does the token survive whatever
 * the person has to do next.
 */

import AcceptInvitationScreen from '../invitations/[token]';
import { renderWithProviders, userEvent, waitFor } from '../../test/utils';

const mockPush = jest.fn();
const mockReplace = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  useLocalSearchParams: () => ({ token: 'invite-token-abc' }),
}));

const mockAuth = { isAuthenticated: false, isLoading: false };

jest.mock('../../store/auth', () => ({
  useAuth: () => mockAuth,
}));

const mockApiCall = jest.fn();

jest.mock('../../lib/api', () => ({
  ...jest.requireActual('@app/shared/api'),
  apiCall: (...args: unknown[]) => mockApiCall(...args),
}));

jest.mock('../../store/toast', () => ({
  useToast: () => ({ error: jest.fn(), success: jest.fn(), info: jest.fn() }),
}));

function renderScreen() {
  return renderWithProviders(<AcceptInvitationScreen />);
}

beforeEach(() => {
  jest.clearAllMocks();
  mockAuth.isAuthenticated = false;
  mockAuth.isLoading = false;
});

describe('when nobody is signed in', () => {
  it('sends them to sign in with a way back', async () => {
    // The bug: `replace('/profile')` after sign-in destroyed the stack and
    // the token with it, so the person arrived on their profile having joined
    // nothing. The redirect is what makes the flow resumable.
    const user = userEvent.setup();
    const view = await renderScreen();

    await user.press(view.getByText('Log in'));

    expect(mockPush).toHaveBeenCalledWith({
      pathname: '/login',
      params: { redirect: '/invitations/invite-token-abc' },
    });
  });

  it('offers sign-up with the same way back', async () => {
    const user = userEvent.setup();
    const view = await renderScreen();

    await user.press(view.getByText('Create an account'));

    expect(mockPush).toHaveBeenCalledWith({
      pathname: '/signup',
      params: { redirect: '/invitations/invite-token-abc' },
    });
  });

  it('does not accept anything before there is an account to accept with', async () => {
    await renderScreen();

    expect(mockApiCall).not.toHaveBeenCalled();
  });
});

describe('when signed in', () => {
  it('accepts the invitation the URL names', async () => {
    mockAuth.isAuthenticated = true;
    mockApiCall.mockResolvedValue({ status: 'success' });
    const user = userEvent.setup();
    const view = await renderScreen();

    await user.press(view.getByText('Accept'));

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith(
        expect.objectContaining({ data: { token: 'invite-token-abc' } }),
      );
      expect(mockReplace).toHaveBeenCalledWith('/organization');
    });
  });

  it('stays put when the invitation is refused', async () => {
    mockAuth.isAuthenticated = true;
    mockApiCall.mockRejectedValue(new Error('expired'));
    const user = userEvent.setup();
    const view = await renderScreen();

    await user.press(view.getByText('Accept'));

    await waitFor(() => expect(mockApiCall).toHaveBeenCalled());
    expect(mockReplace).not.toHaveBeenCalled();
  });
});
