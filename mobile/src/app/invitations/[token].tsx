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

import { appRoutes } from '@app/shared/routes';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Text, useTheme } from 'react-native-paper';

import { FeatureOff } from '../../components/FeatureOff';
import { Screen, ScreenHeader } from '../../components/Screen';
import { apiCall } from '../../lib/api';
import { flags } from '../../lib/config';
import { routes } from '../../lib/routes';
import { useErrorMessage } from '../../lib/useErrorMessage';
import { useAuth } from '../../store/auth';
import { useToast } from '../../store/toast';
import type { AppTheme } from '../../theme/paper';

export default function AcceptInvitationScreen() {
  const theme = useTheme<AppTheme>();
  const router = useRouter();
  const { token } = useLocalSearchParams<{ token: string }>();
  // This screen's own path, to hand to the sign-in screen as a destination.
  const returnHere = appRoutes.acceptInvitation(token);
  const { t } = useTranslation();
  const { isAuthenticated, isLoading } = useAuth();
  const toast = useToast();
  const describe = useErrorMessage();

  const [submitting, setSubmitting] = useState(false);

  async function accept() {
    setSubmitting(true);
    try {
      await apiCall({
        url: routes.api.organizations.acceptInvitation(),
        method: 'POST',
        data: { token },
      });
      toast.success(t('invitationJoined'));
      router.replace('/organization');
    } catch (error) {
      toast.error(describe(error, 'invitationFailed'));
    } finally {
      setSubmitting(false);
    }
  }

  if (!flags.organizations) {
    return (
      <FeatureOff
        feature={t('team')}
        clientFlag="EXPO_PUBLIC_ORGANIZATIONS_ENABLED"
        serverFlag="ORGANIZATIONS_ENABLED"
      />
    );
  }

  if (isLoading) {
    return <Screen loading />;
  }

  if (!isAuthenticated) {
    return (
      <Screen>
        <ScreenHeader title={t('invitationTitle')} subtitle={t('invitationSignInHelp')} />
        <Text
          variant="bodySmall"
          style={{ marginBottom: theme.spacing(2), color: theme.colors.onSurfaceVariant }}
        >
          {t('invitationUseAddress')}
        </Text>
        {/* The `redirect` is what makes this flow work at all. Signing in
            ends with `replace`, which destroys the stack -- and this screen's
            URL is the only place the invitation token exists, so without a
            destination to come back to the token is simply gone and the
            person lands on their profile having joined nothing. */}
        <Button
          mode="contained"
          onPress={() =>
            router.push({ pathname: '/login', params: { redirect: returnHere } })
          }
        >
          {t('login')}
        </Button>
        <Button
          mode="outlined"
          onPress={() =>
            router.push({ pathname: '/signup', params: { redirect: returnHere } })
          }
        >
          {t('createAccount')}
        </Button>
      </Screen>
    );
  }

  return (
    <Screen>
      <ScreenHeader title={t('invitationAcceptTitle')} subtitle={t('invitationAcceptHelp')} />
      <Button mode="contained" onPress={accept} loading={submitting} disabled={submitting}>
        {t('invitationAccept')}
      </Button>
    </Screen>
  );
}
