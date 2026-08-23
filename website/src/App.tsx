import { Box, CircularProgress } from '@mui/material';
import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';

import ProtectedRoute from './components/common/ProtectedRoute';
import Toast from './components/common/Toast';
import Footer from './components/layout/Footer';
import Header from './components/layout/Header';
import { useAuthBootstrap } from './store/auth';

const HomePage = lazy(() => import('./components/pages/HomePage'));
const LoginPage = lazy(() => import('./components/pages/LoginPage'));
const SignUpPage = lazy(() => import('./components/pages/SignUpPage'));
const PasswordResetPage = lazy(() => import('./components/pages/PasswordResetPage'));
const ConfirmNewPasswordPage = lazy(() => import('./components/pages/ConfirmNewPasswordPage'));
const VerifyEmailPage = lazy(() => import('./components/pages/VerifyEmailPage'));
const ProfilePage = lazy(() => import('./components/pages/ProfilePage'));
const SubscriptionPage = lazy(() => import('./components/pages/SubscriptionPage'));
const OrganizationPage = lazy(() => import('./components/pages/OrganizationPage'));
const AcceptInvitationPage = lazy(() => import('./components/pages/AcceptInvitationPage'));

// Billing is optional on the backend too (STRIPE_ENABLED). Keep the two in
// step, or the plans page will 404 against the API.
const BILLING_ENABLED = import.meta.env.VITE_STRIPE_ENABLED === 'true';

// Same contract for teams: the routes only exist when the backend's
// ORGANIZATIONS_ENABLED matches, or they 404 against the API.
const ORGANIZATIONS_ENABLED = import.meta.env.VITE_ORGANIZATIONS_ENABLED === 'true';

function PageFallback() {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
      <CircularProgress />
    </Box>
  );
}

export default function App() {
  // Resolve the session once, before any route renders.
  useAuthBootstrap();

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Header />
      <Toast />
      <Box component="main" sx={{ flexGrow: 1 }}>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignUpPage />} />
            <Route path="/reset-password" element={<PasswordResetPage />} />
            <Route path="/confirm-password/:uid/:token" element={<ConfirmNewPasswordPage />} />
            <Route path="/verify-email/:uid/:token" element={<VerifyEmailPage />} />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <ProfilePage />
                </ProtectedRoute>
              }
            />
            {BILLING_ENABLED && (
              <Route
                path="/subscription"
                element={
                  <ProtectedRoute>
                    <SubscriptionPage />
                  </ProtectedRoute>
                }
              />
            )}
            {ORGANIZATIONS_ENABLED && (
              <>
                <Route
                  path="/organization"
                  element={
                    <ProtectedRoute>
                      <OrganizationPage />
                    </ProtectedRoute>
                  }
                />
                {/* Not wrapped in ProtectedRoute: the page itself sends an
                    anonymous visitor to log in and returns them here, so the
                    token in the URL survives the round trip. */}
                <Route path="/invitations/:token" element={<AcceptInvitationPage />} />
              </>
            )}
            <Route path="*" element={<HomePage />} />
          </Routes>
        </Suspense>
      </Box>
      <Footer />
    </Box>
  );
}
