import { ThemeProvider } from '@mui/material/styles';
import { render, screen } from '@testing-library/react';
import { Provider, useSetAtom } from 'jotai';
import { useEffect, type ReactNode } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { authStatusAtom, userAtom, type AuthStatus } from '../../store/auth';
import { makeUser } from '../../test/utils';
import theme from '../../styles/theme';
import ProtectedRoute from './ProtectedRoute';

function SeedAuth({
  status,
  emailVerified = true,
  children,
}: {
  status: AuthStatus;
  emailVerified?: boolean;
  children: ReactNode;
}) {
  const setStatus = useSetAtom(authStatusAtom);
  const setUser = useSetAtom(userAtom);

  useEffect(() => {
    setStatus(status);
    setUser(status === 'authenticated' ? makeUser({ email_verified: emailVerified }) : null);
  }, [status, emailVerified, setStatus, setUser]);

  return children;
}

function renderGuarded(status: AuthStatus, options: { emailVerified?: boolean; requireVerifiedEmail?: boolean } = {}) {
  return render(
    <Provider>
      <MemoryRouter initialEntries={['/secret']}>
        <ThemeProvider theme={theme}>
          <SeedAuth status={status} emailVerified={options.emailVerified}>
            <Routes>
              <Route path="/login" element={<div>login page</div>} />
              <Route path="/profile" element={<div>profile page</div>} />
              <Route
                path="/secret"
                element={
                  <ProtectedRoute requireVerifiedEmail={options.requireVerifiedEmail}>
                    <div>secret content</div>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </SeedAuth>
        </ThemeProvider>
      </MemoryRouter>
    </Provider>,
  );
}

describe('ProtectedRoute', () => {
  it('shows a spinner while the session is still being resolved', () => {
    // The old version redirected immediately, which bounced signed-in users
    // to /login on every hard refresh.
    renderGuarded('loading');

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    expect(screen.queryByText('login page')).not.toBeInTheDocument();
    expect(screen.queryByText('secret content')).not.toBeInTheDocument();
  });

  it('redirects an anonymous visitor to the login page', () => {
    renderGuarded('anonymous');

    expect(screen.getByText('login page')).toBeInTheDocument();
  });

  it('renders the route for an authenticated user', () => {
    renderGuarded('authenticated');

    expect(screen.getByText('secret content')).toBeInTheDocument();
  });

  it('keeps an unverified user out of a route that requires verification', () => {
    renderGuarded('authenticated', { emailVerified: false, requireVerifiedEmail: true });

    expect(screen.getByText('profile page')).toBeInTheDocument();
  });

  it('lets a verified user into a route that requires verification', () => {
    renderGuarded('authenticated', { emailVerified: true, requireVerifiedEmail: true });

    expect(screen.getByText('secret content')).toBeInTheDocument();
  });
});
