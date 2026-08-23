/**
 * Redeem an invitation token from an emailed link.
 *
 * The endpoint requires a signed-in user, because the invitation is bound to
 * the address it was sent to and there is nothing to check it against
 * otherwise. Anyone arriving here signed out is sent to log in first.
 */

import { Alert, Box, Button, CircularProgress, Container } from '@mui/material';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, useNavigate, useParams } from 'react-router-dom';

import { apiCall } from '../../lib/api';
import { routes } from '../../lib/routes';
import { useAuth } from '../../store/auth';

export default function AcceptInvitationPage() {
  const { token } = useParams<{ token: string }>();
  const { user, isLoading } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [error, setError] = useState<string | null>(null);
  const [accepting, setAccepting] = useState(true);

  useEffect(() => {
    if (isLoading || !user || !token) return;

    let cancelled = false;
    void (async () => {
      try {
        await apiCall({
          method: 'post',
          url: routes.api.organizations.acceptInvitation(),
          data: { token },
        });
        if (!cancelled) navigate(routes.app.organization, { replace: true });
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : t('genericError'));
          setAccepting(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isLoading, user, token, navigate, t]);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!user) {
    // Come back here once they have a session to bind the invitation to.
    return <Navigate to={routes.app.login} state={{ from: window.location.pathname }} replace />;
  }

  return (
    <Container maxWidth="sm" sx={{ py: 8 }}>
      {error ? (
        <>
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
          <Button variant="contained" onClick={() => navigate(routes.app.home)}>
            {t('orgBackHome')}
          </Button>
        </>
      ) : (
        accepting && (
          <Box sx={{ display: 'flex', justifyContent: 'center' }}>
            <CircularProgress />
          </Box>
        )
      )}
    </Container>
  );
}
