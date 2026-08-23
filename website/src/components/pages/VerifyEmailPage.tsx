import { Alert, Box, Button, CircularProgress, Container } from '@mui/material';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { apiCall } from '../../lib/api';
import { routes } from '../../lib/routes';
import { useAuth } from '../../store/auth';

type VerificationState = 'checking' | 'verified' | 'failed';

export default function VerifyEmailPage() {
  const { t } = useTranslation();
  const { uid, token } = useParams<{ uid: string; token: string }>();
  const { refresh } = useAuth();
  // Derived at mount rather than set from inside the effect: a synchronous
  // setState in an effect body causes a cascading re-render.
  const [state, setState] = useState<VerificationState>(() =>
    uid && token ? 'checking' : 'failed',
  );

  useEffect(() => {
    if (!uid || !token) return;

    let cancelled = false;

    (async () => {
      try {
        await apiCall({
          method: 'POST',
          url: routes.api.auth.verifyEmail(),
          data: { uid, token },
        });
        if (cancelled) return;
        setState('verified');
        // Pick up the new email_verified flag if this user is signed in.
        await refresh();
      } catch {
        if (!cancelled) setState('failed');
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [uid, token, refresh]);

  if (state === 'checking') {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="xs">
      <Box sx={{ mt: 8 }}>
        <Alert severity={state === 'verified' ? 'success' : 'error'}>
          {state === 'verified' ? t('emailVerified') : t('invalidVerificationLink')}
        </Alert>
        <Button
          component={Link}
          to={state === 'verified' ? '/profile' : '/login'}
          fullWidth
          variant="contained"
          sx={{ mt: 2 }}
        >
          {state === 'verified' ? t('goToProfile') : t('backToLogin')}
        </Button>
      </Box>
    </Container>
  );
}
