/**
 * Accept an invitation to an organization.
 *
 * `/invitations/<token>` -- emailed by the backend, claimed by the
 * association documents, routed by this filename.
 *
 * Unlike the other two deep links this one *does* need a session: accepting
 * joins an account to a team, so there has to be an account. The token
 * survives the detour because it is in the URL this screen was opened with,
 * and the sign-in screen returns here rather than to the home screen.
 */

import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Button, Text, useTheme } from 'react-native-paper';

import { Screen, ScreenHeader } from '../../components/Screen';
import { ApiError, apiCall } from '../../lib/api';
import { flags } from '../../lib/config';
import { routes } from '../../lib/routes';
import { useAuth } from '../../store/auth';
import { useToast } from '../../store/toast';
import type { AppTheme } from '../../theme/paper';

export default function AcceptInvitationScreen() {
  const theme = useTheme<AppTheme>();
  const router = useRouter();
  const { token } = useLocalSearchParams<{ token: string }>();
  const { isAuthenticated, isLoading } = useAuth();
  const toast = useToast();

  const [submitting, setSubmitting] = useState(false);

  async function accept() {
    setSubmitting(true);
    try {
      await apiCall({
        url: routes.api.organizations.acceptInvitation(),
        method: 'POST',
        data: { token },
        errorMessage: 'That invitation could not be accepted.',
      });
      toast.success('You have joined the organization.');
      router.replace('/organization');
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : 'That invitation could not be accepted.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (!flags.organizations) {
    return (
      <Screen>
        <ScreenHeader
          title="Not available"
          subtitle="Teams are switched off in this app. Check EXPO_PUBLIC_ORGANIZATIONS_ENABLED."
        />
      </Screen>
    );
  }

  if (isLoading) {
    return <Screen loading />;
  }

  if (!isAuthenticated) {
    return (
      <Screen>
        <ScreenHeader
          title="You have been invited"
          subtitle="Sign in or create an account to accept this invitation."
        />
        <Text
          variant="bodySmall"
          style={{ marginBottom: theme.spacing(2), color: theme.colors.onSurfaceVariant }}
        >
          Use the address the invitation was sent to.
        </Text>
        {/* `push`, not `replace`: the back gesture has to return here, and
            this screen's URL is the only place the token exists. */}
        <Button mode="contained" onPress={() => router.push('/login')}>
          Sign in
        </Button>
        <Button mode="outlined" onPress={() => router.push('/signup')}>
          Create an account
        </Button>
      </Screen>
    );
  }

  return (
    <Screen>
      <ScreenHeader
        title="Accept your invitation"
        subtitle="You will join the organization that invited you."
      />
      <Button mode="contained" onPress={accept} loading={submitting} disabled={submitting}>
        Accept
      </Button>
    </Screen>
  );
}
