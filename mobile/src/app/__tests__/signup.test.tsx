/**
 * The sign-up screen.
 *
 * What is worth pinning here is the username: it is the one field on this
 * form that may be left empty, and a `required` rule creeping back onto it
 * would be invisible until someone without a handle tried to sign up.
 */

import SignUpScreen from '../signup';
import { ApiError } from '../../lib/api';
import { renderWithProviders, userEvent, waitFor } from '../../test/utils';

const mockPush = jest.fn();
const mockReplace = jest.fn();
const mockParams: { redirect?: string } = {};

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  useLocalSearchParams: () => mockParams,
}));

const mockRegister = jest.fn();

jest.mock('../../store/auth', () => ({
  useAuth: () => ({ register: mockRegister }),
}));

const mockToastError = jest.fn();

jest.mock('../../store/toast', () => ({
  useToast: () => ({ error: mockToastError, success: jest.fn(), info: jest.fn() }),
}));

const PASSWORD = 'sufficiently-long-passphrase-9';

beforeEach(() => {
  jest.clearAllMocks();
  delete mockParams.redirect;
});

type Rendered = Awaited<ReturnType<typeof renderWithProviders>>;

async function fillTheRequiredFields(view: Rendered) {
  const user = userEvent.setup();

  await user.type(view.getByLabelText('Email'), 'ada@example.com');
  await user.type(view.getByLabelText('First name'), 'Ada');
  await user.type(view.getByLabelText('Last name'), 'Lovelace');
  await user.type(view.getByLabelText('Password'), PASSWORD);
  await user.type(view.getByLabelText('Confirm password'), PASSWORD);

  return user;
}

it('creates an account without a username', async () => {
  mockRegister.mockResolvedValue({ id: 1 });
  const view = await renderWithProviders(<SignUpScreen />);

  const user = await fillTheRequiredFields(view);
  await user.press(view.getByText('Create account'));

  await waitFor(() => {
    expect(mockRegister).toHaveBeenCalledWith(
      // Empty rather than absent, which the backend reads as "none" too.
      expect.objectContaining({ email: 'ada@example.com', username: '' }),
    );
  });
});

it('sends a username when one is given', async () => {
  mockRegister.mockResolvedValue({ id: 1 });
  const view = await renderWithProviders(<SignUpScreen />);

  const user = await fillTheRequiredFields(view);
  await user.type(view.getByLabelText('Username (optional)'), 'ada');
  await user.press(view.getByText('Create account'));

  await waitFor(() => {
    expect(mockRegister).toHaveBeenCalledWith(expect.objectContaining({ username: 'ada' }));
  });
});

it('puts a rejected username back on its own field', async () => {
  mockRegister.mockRejectedValue(
    new ApiError('Registration failed.', 400, {
      username: ['A user with that username already exists.'],
    }),
  );
  const view = await renderWithProviders(<SignUpScreen />);

  const user = await fillTheRequiredFields(view);
  await user.type(view.getByLabelText('Username (optional)'), 'ada');
  await user.press(view.getByText('Create account'));

  await waitFor(() => {
    expect(view.getByText('A user with that username already exists.')).toBeTruthy();
  });
});
