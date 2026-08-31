import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { http } from '../../lib/api';
import { makeUser, renderWithProviders, screen, waitFor } from '../../test/utils';
import SignUpPage from './SignUpPage';

function mockRequest() {
  return vi.spyOn(http, 'request').mockResolvedValue({
    data: { status: 'success', data: { user: makeUser(), csrfToken: 'rotated' } },
  });
}

async function fillTheRequiredFields() {
  await userEvent.type(screen.getByLabelText(/first name/i), 'Ada');
  await userEvent.type(screen.getByLabelText(/last name/i), 'Lovelace');
  await userEvent.type(screen.getByLabelText(/^email/i), 'ada@example.com');
  await userEvent.type(screen.getByLabelText(/^password/i), 'sufficiently-long-passphrase-9');
  await userEvent.type(screen.getByLabelText(/confirm password/i), 'sufficiently-long-passphrase-9');
}

describe('SignUpPage', () => {
  beforeEach(() => {
    // The request interceptor fetches a CSRF token before any POST.
    vi.spyOn(http, 'get').mockResolvedValue({
      data: { status: 'success', data: { csrfToken: 'test-token' } },
    });
  });

  it('registers without a username', async () => {
    const request = mockRequest();
    renderWithProviders(<SignUpPage />);

    await fillTheRequiredFields();
    await userEvent.click(screen.getByRole('button', { name: /sign up/i }));

    await waitFor(() => expect(request).toHaveBeenCalledTimes(1));
    expect(request).toHaveBeenCalledWith(
      expect.objectContaining({
        url: '/api/v1/auth/register/',
        // Empty rather than absent, which the backend reads as "none" too.
        data: expect.objectContaining({ email: 'ada@example.com', username: '' }),
      }),
    );
  });

  it('sends a username when one is given', async () => {
    const request = mockRequest();
    renderWithProviders(<SignUpPage />);

    await fillTheRequiredFields();
    await userEvent.type(screen.getByLabelText(/username/i), 'ada');
    await userEvent.click(screen.getByRole('button', { name: /sign up/i }));

    await waitFor(() => expect(request).toHaveBeenCalledTimes(1));
    expect(request).toHaveBeenCalledWith(
      expect.objectContaining({ data: expect.objectContaining({ username: 'ada' }) }),
    );
  });

  it('still refuses to submit without an email address', async () => {
    const request = mockRequest();
    renderWithProviders(<SignUpPage />);

    await userEvent.click(screen.getByRole('button', { name: /sign up/i }));

    expect(await screen.findByText('Email is required')).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
  });

  it('puts a rejected username back on its own field', async () => {
    vi.spyOn(http, 'request').mockRejectedValue(
      Object.assign(new Error('Request failed'), {
        isAxiosError: true,
        response: {
          status: 400,
          data: {
            status: 'error',
            message: 'Registration failed.',
            errors: { username: ['A user with that username already exists.'] },
          },
        },
      }),
    );
    renderWithProviders(<SignUpPage />);

    await fillTheRequiredFields();
    await userEvent.type(screen.getByLabelText(/username/i), 'ada');
    await userEvent.click(screen.getByRole('button', { name: /sign up/i }));

    expect(
      await screen.findByText('A user with that username already exists.'),
    ).toBeInTheDocument();
  });
});
