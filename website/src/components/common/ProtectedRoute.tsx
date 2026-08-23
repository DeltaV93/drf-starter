import { CircularProgress, Box } from '@mui/material';
import type { ReactElement } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { useAuth } from '../../store/auth';

interface ProtectedRouteProps {
  children: ReactElement;
  /** Also require a confirmed email address. */
  requireVerifiedEmail?: boolean;
}

/**
 * Gate a route on the session.
 *
 * Waits for the session check to finish before deciding. Redirecting while
 * the answer is still 'loading' would bounce every authenticated user to the
 * login page on a hard refresh.
 */
export default function ProtectedRoute({
  children,
  requireVerifiedEmail = false,
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireVerifiedEmail && !user?.email_verified) {
    return <Navigate to="/profile" replace />;
  }

  return children;
}
