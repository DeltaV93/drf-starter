import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import i18n from '../il8n.ts';
import ConfirmNewPasswordPage from '../components/pages/ConfirmNewPasswordPage';
import { apiCall } from '../utils/api';

// Mock the apiCall function
jest.mock('../../utils/apiHelper', () => ({
  apiCall: jest.fn(),
}));

// Mock the useNavigate hook
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  useParams: () => ({ userId: 'Mg', token: 'fb0abf63dbef6e0bca466860606b8d85' }),
}));

const renderComponent = () =>
  render(
    <BrowserRouter>
      <I18nextProvider i18n={i18n}>
        <ConfirmNewPasswordPage />
      </I18nextProvider>
    </BrowserRouter>
  );

describe('ConfirmNewPasswordPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders and verifies token', async () => {
    (apiCall as jest.Mock).mockResolvedValueOnce({ data: { isValid: true } });
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Reset Password')).toBeInTheDocument();
    });

    expect(apiCall).toHaveBeenCalledWith({
      method: 'POST',
      url: '/api/verify-reset-token/',
      data: { userId: 'Mg', token: 'fb0abf63dbef6e0bca466860606b8d85' },
    });
  });

  it('shows error for invalid token', async () => {
    (apiCall as jest.Mock).mockRejectedValueOnce(new Error('Invalid token'));
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Invalid reset link')).toBeInTheDocument();
    });

    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });

  it('submits new password successfully', async () => {
    (apiCall as jest.Mock)
      .mockResolvedValueOnce({ data: { isValid: true } })
      .mockResolvedValueOnce({ data: { success: true } });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByLabelText('New Password')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('New Password'), { target: { value: 'NewPassword123!' } });
    fireEvent.change(screen.getByLabelText('Confirm Password'), { target: { value: 'NewPassword123!' } });

    fireEvent.click(screen.getByText('Reset Password'));

    await waitFor(() => {
      expect(apiCall).toHaveBeenCalledWith({
        method: 'POST',
        url: '/api/reset-password/',
        data: { userId: 'Mg', token: 'fb0abf63dbef6e0bca466860606b8d85', newPassword: 'NewPassword123!' },
      });
    });

    expect(screen.getByText('Password reset successful')).toBeInTheDocument();
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });

  it('shows error for password mismatch', async () => {
    (apiCall as jest.Mock).mockResolvedValueOnce({ data: { isValid: true } });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByLabelText('New Password')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('New Password'), { target: { value: 'NewPassword123!' } });
    fireEvent.change(screen.getByLabelText('Confirm Password'), { target: { value: 'DifferentPassword123!' } });

    fireEvent.click(screen.getByText('Reset Password'));

    expect(screen.getByText('Passwords don\'t match')).toBeInTheDocument();
  });

  it('shows password validation errors', async () => {
    (apiCall as jest.Mock).mockResolvedValueOnce({ data: { isValid: true } });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByLabelText('New Password')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('New Password'), { target: { value: 'weak' } });
    fireEvent.change(screen.getByLabelText('Confirm Password'), { target: { value: 'weak' } });

    fireEvent.click(screen.getByText('Reset Password'));

    expect(screen.getByText('Password must be at least 8 characters long')).toBeInTheDocument();
    expect(screen.getByText('Password must contain at least one uppercase letter')).toBeInTheDocument();
    expect(screen.getByText('Password must contain at least one number')).toBeInTheDocument();
    expect(screen.getByText('Password must contain at least one special character')).toBeInTheDocument();
  });
});