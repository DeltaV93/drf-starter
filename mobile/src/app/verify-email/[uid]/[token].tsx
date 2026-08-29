/**
 * The screen an emailed verification link lands on.
 *
 * The filename is the routing. `/verify-email/<uid>/<token>` is what the
 * backend puts in the email and what the association documents claim, so
 * expo-router matches it here with no configuration -- and renaming this file
 * silently breaks every verification email ever sent. `deepLinks.test.ts`
 * is what stops that.
 *
 * No sign-in required. The token in the URL is the credential, and requiring
 * a session would strand exactly the person the email is for: someone who
 * registered on a laptop and opened the email on their phone.
 */

import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Button } from 'react-native-paper';

import { Screen, ScreenHeader } from '../../../components/Screen';
import { ApiError, apiCall } from '../../../lib/api';
import { routes } from '../../../lib/routes';
import { useAuth } from '../../../store/auth';

type Outcome = 'checking' | 'verified' | 'failed';

export default function VerifyEmailScreen() {
  const router = useRouter();
  const { uid, token } = useLocalSearchParams<{ uid: string; token: string }>();
  const { isAuthenticated, refresh } = useAuth();

  const [outcome, setOutcome] = useState<Outcome>('checking');
  const [message, setMessage] = useState('');

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const envelope = await apiCall({
          url: routes.api.auth.verifyEmail(),
          method: 'POST',
          data: { uid, token },
          errorMessage: 'That link is no longer valid.',
        });
        if (cancelled) return;

        setMessage(envelope.message ?? 'Your email address is confirmed.');
        setOutcome('verified');

        // The signed-in user's `email_verified` just changed, and every
        // screen showing "please confirm your address" reads it from the
        // store. Without this the banner stays up until the next launch.
        if (isAuthenticated) await refresh();
      } catch (error) {
        if (cancelled) return;
        setMessage(
          error instanceof ApiError ? error.message : 'That link is no longer valid.',
        );
        setOutcome('failed');
      }
    })();

    return () => {
      cancelled = true;
    };
    // Runs once for the token in the URL. `refresh` and `isAuthenticated`
    // are deliberately not dependencies: re-running would re-post a token the
    // backend has already spent, and answer "no longer valid" for a
    // verification that had just succeeded.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uid, token]);

  return (
    <Screen loading={outcome === 'checking'}>
      <ScreenHeader
        title={outcome === 'verified' ? 'Email confirmed' : 'That link did not work'}
        subtitle={message}
      />
      <Button
        mode="contained"
        onPress={() => router.replace(isAuthenticated ? '/profile' : '/login')}
      >
        Continue
      </Button>
    </Screen>
  );
}
