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

    expect(await screen.findByText('Username is required')).toBeInTheDocument();
    expect(screen.getByText('Password is required')).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
  });

  it('posts the credentials to the login endpoint', async () => {
    const request = mockRequest().mockResolvedValue({
      data: { status: 'success', data: { user: makeUser(), csrfToken: 'rotated' } },
    });
    renderWithProviders(<LoginPage />);

    await userEvent.type(screen.getByLabelText(/username/i), 'ada');
    await userEvent.type(screen.getByLabelText(/password/i), 'hunter2hunter2');
    await userEvent.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(() => expect(request).toHaveBeenCalledTimes(1));
    expect(request).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'POST',
        url: '/api/v1/auth/login/',
        data: { username: 'ada', password: 'hunter2hunter2' },
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

    await userEvent.type(screen.getByLabelText(/username/i), 'ada');
    await userEvent.type(screen.getByLabelText(/password/i), 'wrong-password');
    await userEvent.click(screen.getByRole('button', { name: /log in/i }));

    expect(await screen.findByText('Login failed.')).toBeInTheDocument();
  });
});
