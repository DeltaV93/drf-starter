/**
 * The sign-in screen, and the branch that is easy to get wrong.
 *
 * A password can be correct and still not sign anyone in. The backend answers
 * that case with a challenge and no tokens, and a screen that navigated
 * straight into the app on any 200 would show a signed-out shell to someone
 * who had, as far as they could tell, just signed in.
 */

import LoginScreen from '../login';
import { renderWithProviders, userEvent, waitFor } from '../../test/utils';

const mockPush = jest.fn();
const mockReplace = jest.fn();
const mockParams: { redirect?: string } = {};

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  useLocalSearchParams: () => mockParams,
}));

const mockLogin = jest.fn();

jest.mock('../../store/auth', () => ({
  useAuth: () => ({ login: mockLogin }),
}));

const mockToastError = jest.fn();

jest.mock('../../store/toast', () => ({
  useToast: () => ({ error: mockToastError, success: jest.fn(), info: jest.fn() }),
}));

function renderScreen() {
  return renderWithProviders(<LoginScreen />);
}

beforeEach(() => {
  jest.clearAllMocks();
  delete mockParams.redirect;
});

it('asks for an identifier and a password', async () => {
  const view = await renderScreen();

  expect(view.getByLabelText('Email or username')).toBeTruthy();
  expect(view.getByLabelText('Password')).toBeTruthy();
});

it('signs in and goes to the app', async () => {
  mockLogin.mockResolvedValue({ status: 'authenticated', user: { id: 1 } });
  const user = userEvent.setup();
  const view = await renderScreen();

  await user.type(view.getByLabelText('Email or username'), 'ada@example.com');
  await user.type(view.getByLabelText('Password'), 'correct horse');
  await user.press(view.getByText('Log in'));

  await waitFor(() => {
    expect(mockLogin).toHaveBeenCalledWith({
      identifier: 'ada@example.com',
      password: 'correct horse',
    });
    expect(mockReplace).toHaveBeenCalledWith('/profile');
  });
});

it('carries the challenge to the verification screen instead of signing in', async () => {
  mockLogin.mockResolvedValue({ status: 'two-factor-required', challenge: 'signed-challenge' });
  const user = userEvent.setup();
  const view = await renderScreen();

  await user.type(view.getByLabelText('Email or username'), 'ada@example.com');
  await user.type(view.getByLabelText('Password'), 'correct horse');
  await user.press(view.getByText('Log in'));

  await waitFor(() => {
    expect(mockPush).toHaveBeenCalledWith({
      pathname: '/two-factor',
      // The destination travels with the challenge: the second factor is a
      // detour inside this flow, not the end of it.
      params: { challenge: 'signed-challenge', redirect: '/profile' },
    });
  });
  // The important half: nothing navigated into the app.
  expect(mockReplace).not.toHaveBeenCalled();
});

it('reports a refusal rather than navigating', async () => {
  const { ApiError } = jest.requireActual('@app/shared/api');
  // The fourth argument is `fromServer`. Only the backend's own words are
  // shown as-is; a message this app invented is replaced by the translated
  // fallback, so a Spanish reader never sees a stray English sentence.
  mockLogin.mockRejectedValue(
    new ApiError('Login failed.', 400, { password: ['Wrong.'] }, true),
  );
  const user = userEvent.setup();
  const view = await renderScreen();

  await user.type(view.getByLabelText('Email or username'), 'ada@example.com');
  await user.type(view.getByLabelText('Password'), 'nope');
  await user.press(view.getByText('Log in'));

  await waitFor(() => {
    expect(mockToastError).toHaveBeenCalledWith('Login failed.');
  });
  expect(mockReplace).not.toHaveBeenCalled();
  expect(mockPush).not.toHaveBeenCalled();
});


describe('resuming an interrupted flow', () => {
  // The bug this covers: an emailed invitation sends someone here to sign in,
  // and `replace('/profile')` destroyed the stack along with the invitation
  // token in its URL. They arrived on their profile having joined nothing.
  it('returns to where it was sent from', async () => {
    mockParams.redirect = '/invitations/abc123';
    mockLogin.mockResolvedValue({ status: 'authenticated', user: { id: 1 } });
    const user = userEvent.setup();
    const view = await renderScreen();

    await user.type(view.getByLabelText('Email or username'), 'ada@example.com');
    await user.type(view.getByLabelText('Password'), 'correct horse');
    await user.press(view.getByText('Log in'));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/invitations/abc123');
    });
  });

  it('carries the destination through the second factor', async () => {
    mockParams.redirect = '/invitations/abc123';
    mockLogin.mockResolvedValue({ status: 'two-factor-required', challenge: 'c' });
    const user = userEvent.setup();
    const view = await renderScreen();

    await user.type(view.getByLabelText('Email or username'), 'ada@example.com');
    await user.type(view.getByLabelText('Password'), 'correct horse');
    await user.press(view.getByText('Log in'));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith({
        pathname: '/two-factor',
        params: { challenge: 'c', redirect: '/invitations/abc123' },
      });
    });
  });

  it('will not be sent out of the app', async () => {
    mockParams.redirect = 'https://evil.example.com';
    mockLogin.mockResolvedValue({ status: 'authenticated', user: { id: 1 } });
    const user = userEvent.setup();
    const view = await renderScreen();

    await user.type(view.getByLabelText('Email or username'), 'ada@example.com');
    await user.type(view.getByLabelText('Password'), 'correct horse');
    await user.press(view.getByText('Log in'));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/profile');
    });
  });
});
