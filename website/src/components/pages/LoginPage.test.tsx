import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { http } from '../../lib/api';
import { makeUser, renderWithProviders, screen, waitFor } from '../../test/utils';
import LoginPage from './LoginPage';

function mockRequest() {
  return vi.spyOn(http, 'request');
}

describe('LoginPage', () => {
  beforeEach(() => {
    // The request interceptor fetches a CSRF token before any POST.
    vi.spyOn(http, 'get').mockResolvedValue({
      data: { status: 'success', data: { csrfToken: 'test-token' } },
    });
  });

  it('requires both fields before sending anything', async () => {
    const request = mockRequest();
    renderWithProviders(<LoginPage />);

    await userEvent.click(screen.getByRole('button', { name: /log in/i }));

    expect(await screen.findByText('Enter your email address')).toBeInTheDocument();
    expect(screen.getByText('Password is required')).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
  });

  it('posts the credentials to the login endpoint', async () => {
    const request = mockRequest().mockResolvedValue({
      data: { status: 'success', data: { user: makeUser(), csrfToken: 'rotated' } },
    });
    renderWithProviders(<LoginPage />);

    await userEvent.type(screen.getByLabelText(/email or username/i), 'ada@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'hunter2hunter2');
    await userEvent.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(() => expect(request).toHaveBeenCalledTimes(1));
    expect(request).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'POST',
        url: '/api/v1/auth/login/',
        data: { identifier: 'ada@example.com', password: 'hunter2hunter2' },
      }),
    );
  });

  it('surfaces the backend error message on bad credentials', async () => {
    mockRequest().mockRejectedValue(
      Object.assign(new Error('Request failed'), {
        isAxiosError: true,
        response: { status: 400, data: { status: 'error', message: 'Login failed.' } },
      }),
    );
    renderWithProviders(<LoginPage />);

    await userEvent.type(screen.getByLabelText(/email or username/i), 'ada@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'wrong-password');
    await userEvent.click(screen.getByRole('button', { name: /log in/i }));

    expect(await screen.findByText('Login failed.')).toBeInTheDocument();
  });
});

describe('LoginPage with two-factor', () => {
  beforeEach(() => {
    vi.spyOn(http, 'get').mockResolvedValue({
      data: { status: 'success', data: { csrfToken: 'test-token' } },
    });
  });

  async function submitCredentials() {
    await userEvent.type(screen.getByLabelText(/email or username/i), 'ada@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'hunter2hunter2');
    await userEvent.click(screen.getByRole('button', { name: /log in/i }));
  }

  it('asks for a code instead of signing in when a second factor is enrolled', async () => {
    // The password step answers twoFactorRequired and carries no user. Reading
    // data.user unconditionally used to set the user to undefined while
    // marking the store authenticated -- worse than failing outright.
    mockRequest().mockResolvedValue({
      data: {
        status: 'success',
        data: { twoFactorRequired: true, csrfToken: 'rotated' },
      },
    });
    renderWithProviders(<LoginPage />);

    await submitCredentials();

    expect(await screen.findByLabelText(/^code$/i)).toBeInTheDocument();
    // Not signed in: no redirect happened and the login form is gone.
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
  });

  it('posts the code to the verify endpoint and completes the login', async () => {
    const request = mockRequest()
      .mockResolvedValueOnce({
        data: { status: 'success', data: { twoFactorRequired: true } },
      })
      .mockResolvedValueOnce({
        data: { status: 'success', data: { user: makeUser(), csrfToken: 'rotated' } },
      });
    renderWithProviders(<LoginPage />);

    await submitCredentials();
    await userEvent.type(await screen.findByLabelText(/^code$/i), '123456');
    await userEvent.click(screen.getByRole('button', { name: /verify/i }));

    await waitFor(() => expect(request).toHaveBeenCalledTimes(2));
    expect(request).toHaveBeenLastCalledWith(
      expect.objectContaining({
        method: 'POST',
        url: '/api/v1/auth/2fa/verify/',
        data: { code: '123456' },
      }),
    );
  });

  it('keeps the user on the code step when the code is wrong', async () => {
    mockRequest()
      .mockResolvedValueOnce({
        data: { status: 'success', data: { twoFactorRequired: true } },
      })
      .mockRejectedValueOnce(
        Object.assign(new Error('Request failed'), {
          isAxiosError: true,
          response: {
            status: 400,
            data: { status: 'error', message: 'That code is not correct.' },
          },
        }),
      );
    renderWithProviders(<LoginPage />);

    await submitCredentials();
    await userEvent.type(await screen.findByLabelText(/^code$/i), '000000');
    await userEvent.click(screen.getByRole('button', { name: /verify/i }));

    expect(await screen.findByText('That code is not correct.')).toBeInTheDocument();
    expect(screen.getByLabelText(/^code$/i)).toBeInTheDocument();
  });
});
