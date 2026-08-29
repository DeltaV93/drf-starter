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

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
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
});

it('asks for a username and a password', async () => {
  const view = await renderScreen();

  expect(view.getByLabelText('Username')).toBeTruthy();
  expect(view.getByLabelText('Password')).toBeTruthy();
});

it('signs in and goes to the app', async () => {
  mockLogin.mockResolvedValue({ status: 'authenticated', user: { id: 1 } });
  const user = userEvent.setup();
  const view = await renderScreen();

  await user.type(view.getByLabelText('Username'), 'ada');
  await user.type(view.getByLabelText('Password'), 'correct horse');
  await user.press(view.getByText('Sign in'));

  await waitFor(() => {
    expect(mockLogin).toHaveBeenCalledWith({ username: 'ada', password: 'correct horse' });
    expect(mockReplace).toHaveBeenCalledWith('/profile');
  });
});

it('carries the challenge to the verification screen instead of signing in', async () => {
  mockLogin.mockResolvedValue({ status: 'two-factor-required', challenge: 'signed-challenge' });
  const user = userEvent.setup();
  const view = await renderScreen();

  await user.type(view.getByLabelText('Username'), 'ada');
  await user.type(view.getByLabelText('Password'), 'correct horse');
  await user.press(view.getByText('Sign in'));

  await waitFor(() => {
    expect(mockPush).toHaveBeenCalledWith({
      pathname: '/two-factor',
      params: { challenge: 'signed-challenge' },
    });
  });
  // The important half: nothing navigated into the app.
  expect(mockReplace).not.toHaveBeenCalled();
});

it('reports a refusal rather than navigating', async () => {
  const { ApiError } = jest.requireActual('@app/shared/api');
  mockLogin.mockRejectedValue(new ApiError('Login failed.', 400, { password: ['Wrong.'] }));
  const user = userEvent.setup();
  const view = await renderScreen();

  await user.type(view.getByLabelText('Username'), 'ada');
  await user.type(view.getByLabelText('Password'), 'nope');
  await user.press(view.getByText('Sign in'));

  await waitFor(() => {
    expect(mockToastError).toHaveBeenCalledWith('Login failed.');
  });
  expect(mockReplace).not.toHaveBeenCalled();
  expect(mockPush).not.toHaveBeenCalled();
});
